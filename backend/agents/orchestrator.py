"""LangGraph-style orchestrator for the multi-agent analysis pipeline.

Implements a state machine that coordinates agent execution:

  START → ParserAgent → [GraphAgent, CodeAnalysisAgent] (parallel)
        → [SecurityAgent, ArchitectureAgent, PerformanceAgent] (parallel, depend on graphs)
        → DocumentationAgent (depends on architecture)
        → SynthesisAgent (depends on everything)
        → END

Each transition checks prerequisites in shared memory.
Agents run in parallel where dependencies allow.
"""
import asyncio
import logging
import time
from typing import AsyncGenerator
from datetime import datetime, timezone

from backend.agents.shared_memory import SharedMemory, AgentEvent
from backend.agents.specialized import (
    ParserAgent, GraphAgent, CodeAnalysisAgent,
    SecurityAgent, ArchitectureAgent, PerformanceAgent,
    DocumentationAgent, SynthesisAgent,
)
from backend.analysis.timeline import TimelineAnalyzer
from config.settings import settings

logger = logging.getLogger(__name__)


# State machine definition — which agents run in each phase
PIPELINE_PHASES = [
    {
        "name": "phase_1_parse",
        "label": "Phase 1: Parse & Embed",
        "agents": ["parser"],
        "parallel": False,
    },
    {
        "name": "phase_2_structure",
        "label": "Phase 2: Graphs & Health",
        "agents": ["graph", "code_analysis"],
        "parallel": True,
    },
    {
        "name": "phase_3_deep",
        "label": "Phase 3: Deep Analysis",
        "agents": ["security", "architecture", "performance"],
        "parallel": True,
    },
    {
        "name": "phase_4_docs",
        "label": "Phase 4: Documentation",
        "agents": ["documentation"],
        "parallel": False,
    },
    {
        "name": "phase_5_synthesis",
        "label": "Phase 5: Final Synthesis",
        "agents": ["synthesis"],
        "parallel": False,
    },
]


class Orchestrator:
    """LangGraph-style supervisor that coordinates agent execution.

    Usage:
        memory = SharedMemory()
        orch = Orchestrator(memory)
        async for event in orch.run(repo_url, branch):
            # event is AgentEvent dict — stream to frontend via SSE
            print(event)
    """

    AGENT_CLASSES = {
        "parser": ParserAgent,
        "graph": GraphAgent,
        "code_analysis": CodeAnalysisAgent,
        "security": SecurityAgent,
        "architecture": ArchitectureAgent,
        "performance": PerformanceAgent,
        "documentation": DocumentationAgent,
        "synthesis": SynthesisAgent,
    }

    def __init__(self, memory: SharedMemory):
        self.memory = memory
        self.agents = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()

    def _create_agent(self, name: str):
        cls = self.AGENT_CLASSES.get(name)
        if not cls:
            raise ValueError(f"Unknown agent: {name}")
        agent = cls(self.memory)
        self.agents[name] = agent
        return agent

    async def run(
        self,
        repo_url: str,
        branch: str = "main",
    ) -> AsyncGenerator[dict, None]:
        """Run the full pipeline, yielding events for SSE streaming."""
        t_start = time.monotonic()

        # Initialize shared memory
        await self.memory.clear()
        await self.memory.update({
            "repo.url": repo_url,
            "repo.branch": branch,
            "meta.job_start": datetime.now(timezone.utc).isoformat(),
            "meta.status": "running",
        })

        # Register event listener to forward to generator
        self.memory.on_event(lambda e: self._event_queue.put_nowait(e))

        yield AgentEvent(
            agent_name="supervisor",
            event_type="started",
            message=f"Starting analysis of {repo_url}",
            data={"phases": len(PIPELINE_PHASES), "total_agents": len(self.AGENT_CLASSES)},
        ).to_dict()

        # Execute each phase
        phase_results = {}
        for phase_idx, phase in enumerate(PIPELINE_PHASES):
            phase_name = phase["name"]
            phase_label = phase["label"]

            yield AgentEvent(
                agent_name="supervisor",
                event_type="phase_started",
                message=f"{phase_label} ({phase_idx + 1}/{len(PIPELINE_PHASES)})",
                data={"phase": phase_name, "agents": phase["agents"]},
            ).to_dict()

            t_phase = time.monotonic()

            if phase["parallel"] and len(phase["agents"]) > 1:
                # Run agents in parallel
                results = await self._run_parallel(phase["agents"])
            else:
                # Run agents sequentially
                results = {}
                for agent_name in phase["agents"]:
                    result = await self._run_agent(agent_name)
                    results[agent_name] = result

            phase_ms = int((time.monotonic() - t_phase) * 1000)

            # Drain queued events
            while not self._event_queue.empty():
                event = self._event_queue.get_nowait()
                yield event.to_dict()

            phase_results[phase_name] = results

            yield AgentEvent(
                agent_name="supervisor",
                event_type="phase_completed",
                message=f"{phase_label} completed in {phase_ms}ms",
                data={"phase": phase_name, "duration_ms": phase_ms},
            ).to_dict()

        # Run timeline analysis (non-LLM, uses git)
        try:
            repo_path = await self.memory.get("repo.path")
            if repo_path:
                timeline = TimelineAnalyzer()
                timeline_data = timeline.analyze(repo_path)
                await self.memory.set("analysis.timeline", timeline_data)
        except Exception as e:
            logger.warning(f"Timeline analysis failed: {e}")

        total_ms = int((time.monotonic() - t_start) * 1000)
        await self.memory.set("meta.status", "completed")
        await self.memory.set("meta.duration_ms", total_ms)

        yield AgentEvent(
            agent_name="supervisor",
            event_type="completed",
            message=f"Analysis completed in {total_ms}ms",
            data={"duration_ms": total_ms, "agent_statuses": await self.memory.get_agent_statuses()},
        ).to_dict()

    async def _run_agent(self, agent_name: str) -> dict:
        """Run a single agent."""
        agent = self._create_agent(agent_name)
        return await agent.run()

    async def _run_parallel(self, agent_names: list[str]) -> dict:
        """Run multiple agents in parallel with concurrency limit."""
        sem = asyncio.Semaphore(settings.agent_concurrency)
        results = {}

        async def _run_one(name):
            async with sem:
                result = await self._run_agent(name)
                results[name] = result

        await asyncio.gather(
            *[_run_one(name) for name in agent_names],
            return_exceptions=True,
        )
        return results

    async def build_result(self) -> dict:
        """Build the final AnalysisResult from shared memory."""
        analysis = await self.memory.get_section("analysis")
        graphs = await self.memory.get_section("graphs")
        parsed = await self.memory.get_section("parsed")
        meta = await self.memory.get_section("meta")

        return {
            "status": meta.get("status", "completed"),
            "duration_ms": meta.get("duration_ms"),
            "quick_stats": parsed.get("quick_stats"),
            "repo_overview": analysis.get("repo_overview"),
            "tech_stack": analysis.get("tech_stack"),
            "modules": analysis.get("modules"),
            "file_analyses": analysis.get("file_analyses"),
            "function_analyses": analysis.get("function_analyses"),
            "dependencies": analysis.get("dependencies"),
            "system_flow": analysis.get("system_flow"),
            "flow_diagram": analysis.get("flow_diagram"),
            "production_readiness": analysis.get("production_readiness"),
            "security_analysis": analysis.get("security_analysis"),
            "cost_analysis": analysis.get("cost_analysis"),
            "interview_explainer": analysis.get("interview_explainer"),
            "master_synthesis": analysis.get("master_synthesis"),
            "health_dashboard": analysis.get("health_dashboard"),
            "call_graph": graphs.get("call"),
            "knowledge_graph": graphs.get("knowledge"),
            "recommendations": analysis.get("recommendations"),
            "abstraction_views": analysis.get("abstraction_views"),
            "code_quality": analysis.get("code_quality"),
            "api_contracts": analysis.get("api_contracts"),
            "db_schema": analysis.get("db_schema"),
            "perf_bottlenecks": analysis.get("perf_bottlenecks"),
            "complexity_score": analysis.get("complexity_score"),
            "architecture_patterns": analysis.get("architecture_patterns"),
            "security_threats": analysis.get("security_threats"),
            "failure_modes": analysis.get("failure_modes"),
            "timeline": analysis.get("timeline"),
            "auto_docs": analysis.get("auto_docs"),
        }
