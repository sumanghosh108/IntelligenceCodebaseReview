"""Specialized agents for the distributed multi-agent analysis pipeline.

Each agent reads its inputs from shared memory, runs its analysis,
and writes results back to shared memory.

Agents:
  1. ParserAgent      — repo → structured chunks
  2. GraphAgent       — builds dependency/call/knowledge graphs
  3. CodeAnalysisAgent — file-level insights + health scoring
  4. SecurityAgent    — vulnerabilities + threat model
  5. ArchitectureAgent — system design detection + patterns
  6. PerformanceAgent — bottlenecks + complexity
  7. DocumentationAgent — auto docs + overview
  8. SynthesisAgent   — merges all outputs (runs LAST)
"""
import json
import logging
import time

from backend.agents.base import BaseAgent
from backend.agents.shared_memory import SharedMemory
from backend.utils.helpers import truncate, collection_name_for

logger = logging.getLogger(__name__)


# ============================================================
# 1. Parser Agent — repo → structured chunks + embeddings
# ============================================================
class ParserAgent(BaseAgent):
    name = "parser"
    description = "Parsing source files and building embeddings"

    async def execute(self) -> dict:
        from backend.parsers.code_parser import CodeParser
        from backend.core.repo_manager import RepoManager
        from backend.embeddings.vector_store import vector_store
        from backend.embeddings.hybrid_search import HybridSearchEngine

        repo_url = await self.memory.get("repo.url")
        branch = await self.memory.get("repo.branch", "main")

        # Clone
        await self.emit_progress("Cloning repository")
        repo_manager = RepoManager()
        repo_path = repo_manager.clone(repo_url, branch)

        # Parse
        await self.emit_progress("Parsing source files")
        parser = CodeParser()
        files = repo_manager.list_files(repo_path)
        parsed_files = parser.parse_repo(repo_path, files)

        # Quick stats
        languages = list(set(pf["language"] for pf in parsed_files if pf["language"] != "unknown"))
        total_lines = sum(pf["line_count"] for pf in parsed_files)
        total_functions = sum(len(pf["functions"]) for pf in parsed_files)
        repo_name = repo_url.rstrip("/").split("/")[-1]

        quick_stats = {
            "repo_name": repo_name,
            "total_files": len(parsed_files),
            "total_lines": total_lines,
            "total_functions": total_functions,
            "languages": languages,
            "branch": branch,
        }

        # Gather context
        config_files = repo_manager.get_config_files(repo_path)
        folder_structure = repo_manager.get_folder_structure(repo_path)

        # Embed
        await self.emit_progress(f"Embedding {len(parsed_files)} files")
        collection_name = collection_name_for(repo_url)
        all_chunks = []
        for pf in parsed_files:
            all_chunks.extend(pf["chunks"])
        if all_chunks:
            content_hash = vector_store.compute_content_hash(all_chunks)
            vector_store.embed_chunks(all_chunks, collection_name, content_hash=content_hash)
            # Build hybrid search
            hybrid = HybridSearchEngine(vector_store, collection_name)
            hybrid.build_index(all_chunks)
            await self.memory.set("embeddings.hybrid", hybrid)

        # Store all outputs
        await self.memory.update({
            "repo.path": str(repo_path),
            "repo.name": repo_name,
            "parsed.files": parsed_files,
            "parsed.config_files": config_files,
            "parsed.folder_structure": folder_structure,
            "parsed.quick_stats": quick_stats,
            "embeddings.collection_name": collection_name,
        })

        return {"quick_stats": quick_stats}


# ============================================================
# 2. Graph Agent — builds dependency/call/knowledge graphs
# ============================================================
class GraphAgent(BaseAgent):
    name = "graph"
    description = "Building dependency, call, and knowledge graphs"

    async def execute(self) -> dict:
        from backend.graphs.dependency_graph import DependencyGraphBuilder
        from backend.graphs.call_graph import CallGraphBuilder
        from backend.graphs.knowledge_graph import CodeKnowledgeGraph

        parsed_files = await self.memory.get("parsed.files")

        # Dependency graph
        await self.emit_progress("Building dependency graph")
        dep_builder = DependencyGraphBuilder()
        dep_data = dep_builder.build_from_parsed(parsed_files)

        # Call graph
        await self.emit_progress("Building call graph")
        call_builder = CallGraphBuilder()
        call_data = call_builder.build(parsed_files)

        # Knowledge graph
        await self.emit_progress("Building knowledge graph")
        kg = CodeKnowledgeGraph()
        try:
            kg_summary = kg.build(parsed_files, dep_data, call_data)
            kg_data = {
                "summary": kg_summary,
                "hotspots": kg.get_hotspots(10),
                "module_interactions": kg.get_module_interactions(),
            }
        except Exception as e:
            logger.warning(f"Knowledge graph failed: {e}")
            kg_data = {"error": str(e)}

        await self.memory.update({
            "graphs.dependency": dep_data,
            "graphs.call": call_data,
            "graphs.knowledge": kg_data,
            "graphs.kg_instance": kg,
        })

        return {"dep_data": dep_data, "call_data": call_data, "knowledge_graph": kg_data}


# ============================================================
# 3. Code Analysis Agent — health, quality, file/function analysis
# ============================================================
class CodeAnalysisAgent(BaseAgent):
    name = "code_analysis"
    description = "Analyzing code quality and health"

    async def execute(self) -> dict:
        from backend.scoring.health_scorer import HealthScorer
        from backend.scoring.code_quality_analyzer import CodeQualityAnalyzer
        from backend.llm.model_router import model_router
        from backend.analysis.prompts import SYSTEM_PROMPT

        parsed_files = await self.memory.get("parsed.files")
        config_files = await self.memory.get("parsed.config_files", {})
        folder_structure = await self.memory.get("parsed.folder_structure", {})

        # Health scoring
        await self.emit_progress("Scoring code health")
        scorer = HealthScorer()
        health_dashboard = scorer.score_all(parsed_files, config_files, folder_structure)

        # Code quality (rule-based + AI)
        await self.emit_progress("Analyzing code quality")
        quality_analyzer = CodeQualityAnalyzer()
        rule_issues = quality_analyzer.analyze_rule_based(parsed_files)

        ai_issues = []
        try:
            ai_prompt = quality_analyzer.build_ai_prompt(parsed_files, rule_issues)
            ai_raw = await model_router.generate_json(
                "code_quality", ai_prompt, system_prompt=SYSTEM_PROMPT
            )
            if isinstance(ai_raw, list):
                ai_issues = ai_raw
            elif isinstance(ai_raw, dict) and "issues" in ai_raw:
                ai_issues = ai_raw["issues"]
        except Exception as e:
            logger.warning(f"AI quality critique failed: {e}")

        code_quality = quality_analyzer.merge_results(rule_issues, ai_issues)

        await self.memory.update({
            "analysis.health_dashboard": health_dashboard,
            "analysis.code_quality": code_quality,
        })

        return {"health_dashboard": health_dashboard, "code_quality": code_quality}


# ============================================================
# 4. Security Agent — vulnerabilities + threat model
# ============================================================
class SecurityAgent(BaseAgent):
    name = "security"
    description = "Scanning for security vulnerabilities"

    async def execute(self) -> dict:
        from backend.analysis.advanced_analyzers import SecuritySmellDetector
        from backend.analysis.prompts import SYSTEM_PROMPT, security_analysis_prompt, threat_model_prompt
        from backend.llm.model_router import model_router

        parsed_files = await self.memory.get("parsed.files")
        config_files = await self.memory.get("parsed.config_files", {})
        folder_structure = await self.memory.get("parsed.folder_structure", {})

        # Static security smells
        await self.emit_progress("Running static security scan")
        detector = SecuritySmellDetector()
        security_threats = detector.detect(parsed_files)

        # Build overview context for LLM
        config_context = "\n\n".join(
            f"--- {name} ---\n{content}" for name, content in config_files.items()
        )
        structure_context = json.dumps(folder_structure, indent=2)
        file_summary = []
        for pf in parsed_files[:50]:
            funcs = [f["name"] for f in pf["functions"]]
            file_summary.append(f"  {pf['file_path']} ({pf['language']}) - functions: {funcs}")
        overview_context = (
            f"Config files:\n{truncate(config_context, 3000)}\n\n"
            f"Folder structure:\n{truncate(structure_context, 2000)}\n\n"
            f"Files:\n{truncate(chr(10).join(file_summary), 2000)}"
        )

        # LLM security analysis
        await self.emit_progress("Running AI security analysis")
        code_samples = []
        for pf in parsed_files[:10]:
            code_samples.append(f"--- {pf['file_path']} ---\n{pf['source_preview']}")
        security_ctx = overview_context + "\n\nCode samples:\n" + truncate("\n".join(code_samples), 3000)

        try:
            security_analysis = await model_router.generate_json(
                "security", security_analysis_prompt(security_ctx), system_prompt=SYSTEM_PROMPT
            )
        except Exception as e:
            logger.warning(f"LLM security analysis failed: {e}")
            security_analysis = {"error": str(e)}

        # Threat model
        await self.emit_progress("Building threat model")
        try:
            sec_findings = json.dumps(security_threats, indent=2, default=str)
            llm_threats = await model_router.generate_json(
                "security",
                threat_model_prompt(truncate(overview_context, 3000), truncate(sec_findings, 2000)),
                system_prompt=SYSTEM_PROMPT,
            )
            security_threats["llm_threat_model"] = llm_threats
        except Exception as e:
            logger.warning(f"Threat model failed: {e}")

        # Merge health dashboard security if available
        health = await self.memory.get("analysis.health_dashboard")
        if health and "security" in health:
            security_analysis["deterministic_score"] = health["security"]["score"]
            security_analysis["deterministic_issues"] = health["security"]["issues"]

        await self.memory.update({
            "analysis.security_analysis": security_analysis,
            "analysis.security_threats": security_threats,
        })

        return {"security_analysis": security_analysis, "security_threats": security_threats}


# ============================================================
# 5. Architecture Agent — system design + patterns
# ============================================================
class ArchitectureAgent(BaseAgent):
    name = "architecture"
    description = "Detecting architecture patterns and system design"
    default_timeout = 300  # 5 LLM calls, needs more time

    async def execute(self) -> dict:
        from backend.analysis.advanced_analyzers import (
            ArchitectureDetector, APIContractDetector, DatabaseSchemaDetector,
        )
        from backend.analysis.prompts import (
            SYSTEM_PROMPT, repo_overview_prompt, tech_stack_prompt,
            module_identification_prompt, system_flow_prompt, flow_diagram_prompt,
        )
        from backend.llm.model_router import model_router

        parsed_files = await self.memory.get("parsed.files")
        config_files = await self.memory.get("parsed.config_files", {})
        folder_structure = await self.memory.get("parsed.folder_structure", {})

        config_context = "\n\n".join(
            f"--- {name} ---\n{content}" for name, content in config_files.items()
        )
        structure_context = json.dumps(folder_structure, indent=2)
        file_summary = []
        for pf in parsed_files[:50]:
            funcs = [f["name"] for f in pf["functions"]]
            file_summary.append(f"  {pf['file_path']} ({pf['language']}, {pf['line_count']}L) - functions: {funcs}")
        file_summary_str = "\n".join(file_summary)
        overview_context = (
            f"Config files:\n{truncate(config_context, 3000)}\n\n"
            f"Folder structure:\n{truncate(structure_context, 2000)}\n\n"
            f"Files:\n{truncate(file_summary_str, 2000)}"
        )

        # Deterministic: Architecture patterns
        await self.emit_progress("Detecting architecture patterns")
        arch_detector = ArchitectureDetector()
        arch_patterns = arch_detector.detect(parsed_files, folder_structure, config_files)

        # Deterministic: API contracts
        await self.emit_progress("Detecting API contracts")
        api_detector = APIContractDetector()
        api_contracts = api_detector.detect(parsed_files, config_files)

        # Deterministic: DB schema
        await self.emit_progress("Detecting database schema")
        db_detector = DatabaseSchemaDetector()
        db_schema = db_detector.detect(parsed_files, config_files)

        # LLM: Overview, tech stack, modules (parallel)
        await self.emit_progress("Running AI architecture analysis")
        import asyncio

        async def _overview():
            return await model_router.generate_json(
                "overview", repo_overview_prompt(overview_context), system_prompt=SYSTEM_PROMPT
            )

        async def _tech():
            return await model_router.generate_json(
                "tech_stack", tech_stack_prompt(config_context), system_prompt=SYSTEM_PROMPT
            )

        async def _modules():
            raw = await model_router.generate_json(
                "modules", module_identification_prompt(structure_context), system_prompt=SYSTEM_PROMPT
            )
            if isinstance(raw, list):
                return raw
            elif isinstance(raw, dict) and "raw_response" not in raw:
                return [raw]
            return [raw] if raw else []

        results = await asyncio.gather(
            _overview(), _tech(), _modules(),
            return_exceptions=True,
        )

        repo_overview = results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])}
        tech_stack = results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])}
        modules = results[2] if not isinstance(results[2], Exception) else []

        # System flow (depends on overview + modules)
        await self.emit_progress("Tracing system flow")
        try:
            flow_context = (
                f"Repo overview: {json.dumps(repo_overview)}\n\n"
                f"Modules: {json.dumps(modules)}\n\n"
                f"Files summary:\n{file_summary_str}"
            )
            system_flow = await model_router.generate_json(
                "system_flow", system_flow_prompt(truncate(flow_context, 4000)), system_prompt=SYSTEM_PROMPT
            )
        except Exception as e:
            system_flow = {"error": str(e)}

        # Flow diagram
        try:
            diagram_context = f"Modules: {json.dumps(modules)}\n\nSystem flow: {json.dumps(system_flow)}"
            from backend.analysis.prompts import SYSTEM_PROMPT as SP
            diagram_raw = await model_router.generate(
                "modules", flow_diagram_prompt(truncate(diagram_context, 3000)), system_prompt=SP
            )
            diagram = diagram_raw.strip()
            if diagram.startswith("```"):
                lines = diagram.splitlines()
                lines = [l for l in lines if not l.strip().startswith("```")]
                diagram = "\n".join(lines)
        except Exception:
            diagram = None

        await self.memory.update({
            "analysis.repo_overview": repo_overview,
            "analysis.tech_stack": tech_stack,
            "analysis.modules": modules,
            "analysis.architecture_patterns": arch_patterns,
            "analysis.api_contracts": api_contracts,
            "analysis.db_schema": db_schema,
            "analysis.system_flow": system_flow,
            "analysis.flow_diagram": diagram,
        })

        return {
            "repo_overview": repo_overview,
            "tech_stack": tech_stack,
            "modules": modules,
            "architecture_patterns": arch_patterns,
        }


# ============================================================
# 6. Performance Agent — bottlenecks + complexity
# ============================================================
class PerformanceAgent(BaseAgent):
    name = "performance"
    description = "Detecting performance bottlenecks"

    async def execute(self) -> dict:
        from backend.analysis.advanced_analyzers import PerformanceDetector, ComplexityScorer
        from backend.analysis.advanced_analyzers import FailureModePredictor
        from backend.analysis.prompts import SYSTEM_PROMPT, production_readiness_prompt, failure_analysis_prompt
        from backend.llm.model_router import model_router

        parsed_files = await self.memory.get("parsed.files")
        dep_data = await self.memory.get("graphs.dependency", {})
        call_data = await self.memory.get("graphs.call", {})
        health = await self.memory.get("analysis.health_dashboard", {})
        config_files = await self.memory.get("parsed.config_files", {})
        folder_structure = await self.memory.get("parsed.folder_structure", {})

        # Deterministic analysis (parallel)
        await self.emit_progress("Running performance analysis")
        perf_detector = PerformanceDetector()
        perf_bottlenecks = perf_detector.detect(parsed_files)

        complexity_scorer = ComplexityScorer()
        complexity_score = complexity_scorer.score(parsed_files, dep_data)

        failure_predictor = FailureModePredictor()
        failure_modes = failure_predictor.predict(parsed_files, dep_data, call_data, health or {})

        # LLM: Production readiness
        await self.emit_progress("Checking production readiness")
        config_context = "\n\n".join(
            f"--- {name} ---\n{content}" for name, content in config_files.items()
        )
        structure_context = json.dumps(folder_structure, indent=2)
        file_summary = []
        for pf in parsed_files[:50]:
            funcs = [f["name"] for f in pf["functions"]]
            file_summary.append(f"  {pf['file_path']} ({pf['language']}) - functions: {funcs}")
        overview_context = (
            f"Config files:\n{truncate(config_context, 3000)}\n\n"
            f"Folder structure:\n{truncate(structure_context, 2000)}\n\n"
            f"Files:\n{truncate(chr(10).join(file_summary), 2000)}"
        )

        try:
            production = await model_router.generate_json(
                "production", production_readiness_prompt(overview_context), system_prompt=SYSTEM_PROMPT
            )
            if health and "production_readiness" in health:
                det = health["production_readiness"]
                production["deterministic_score"] = det["score"]
                production["deterministic_details"] = det["details"]
                production["deterministic_issues"] = det["issues"]
        except Exception as e:
            production = {"error": str(e)}

        # LLM: Failure analysis
        try:
            fail_ctx = json.dumps(failure_modes, indent=2, default=str)
            llm_failures = await model_router.generate_json(
                "production",
                failure_analysis_prompt(truncate(overview_context, 3000), truncate(fail_ctx, 2000)),
                system_prompt=SYSTEM_PROMPT,
            )
            failure_modes["llm_analysis"] = llm_failures
        except Exception as e:
            logger.warning(f"Failure analysis LLM failed: {e}")

        await self.memory.update({
            "analysis.perf_bottlenecks": perf_bottlenecks,
            "analysis.complexity_score": complexity_score,
            "analysis.failure_modes": failure_modes,
            "analysis.production_readiness": production,
        })

        return {
            "perf_bottlenecks": perf_bottlenecks,
            "complexity_score": complexity_score,
            "production_readiness": production,
        }


# ============================================================
# 7. Documentation Agent — auto docs + views + interview
# ============================================================
class DocumentationAgent(BaseAgent):
    name = "documentation"
    description = "Generating documentation and views"
    default_timeout = 300  # 4 parallel LLM calls

    async def execute(self) -> dict:
        import asyncio
        from backend.analysis.prompts import (
            SYSTEM_PROMPT, auto_doc_prompt, abstraction_views_prompt,
            interview_explainer_prompt, cost_analysis_prompt,
        )
        from backend.llm.model_router import model_router

        overview = await self.memory.get("analysis.repo_overview", {})
        tech_stack = await self.memory.get("analysis.tech_stack", {})
        modules = await self.memory.get("analysis.modules", [])
        system_flow = await self.memory.get("analysis.system_flow", {})
        api_contracts = await self.memory.get("analysis.api_contracts", {})
        health = await self.memory.get("analysis.health_dashboard", {})
        config_files = await self.memory.get("parsed.config_files", {})

        config_context = "\n\n".join(
            f"--- {name} ---\n{content}" for name, content in config_files.items()
        )

        # Run all doc tasks in parallel
        await self.emit_progress("Generating documentation")

        async def _auto_docs():
            doc_ctx = (
                f"Overview: {json.dumps(overview)}\n"
                f"Tech: {json.dumps(tech_stack)}\n"
                f"Modules: {json.dumps(modules)}\n"
                f"API: {json.dumps(api_contracts)}\n"
                f"Config: {truncate(config_context, 2000)}"
            )
            return await model_router.generate_json(
                "views", auto_doc_prompt(truncate(doc_ctx, 5000)), system_prompt=SYSTEM_PROMPT
            )

        async def _views():
            ctx = (
                f"Overview: {json.dumps(overview)}\n"
                f"Tech: {json.dumps(tech_stack)}\n"
                f"Modules: {json.dumps(modules)}\n"
                f"Flow: {json.dumps(system_flow)}\n"
                f"Health: overall={health.get('overall_score', 'N/A') if health else 'N/A'}"
            )
            return await model_router.generate_json(
                "views", abstraction_views_prompt(truncate(ctx, 4000)), system_prompt=SYSTEM_PROMPT
            )

        async def _interview():
            ctx = (
                f"Overview: {json.dumps(overview)}\n"
                f"Tech: {json.dumps(tech_stack)}\n"
                f"Modules: {json.dumps(modules)}\n"
                f"Flow: {json.dumps(system_flow)}"
            )
            return await model_router.generate_json(
                "interview", interview_explainer_prompt(truncate(ctx, 4000)), system_prompt=SYSTEM_PROMPT
            )

        async def _cost():
            return await model_router.generate_json(
                "cost", cost_analysis_prompt(config_context), system_prompt=SYSTEM_PROMPT
            )

        results = await asyncio.gather(
            _auto_docs(), _views(), _interview(), _cost(),
            return_exceptions=True,
        )

        auto_docs = results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])}
        views = results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])}
        interview = results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])}
        cost = results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])}

        await self.memory.update({
            "analysis.auto_docs": auto_docs,
            "analysis.abstraction_views": views,
            "analysis.interview_explainer": interview,
            "analysis.cost_analysis": cost,
        })

        return {"auto_docs": auto_docs, "abstraction_views": views}


# ============================================================
# 8. Synthesis Agent — merges all outputs (runs LAST)
# ============================================================
class SynthesisAgent(BaseAgent):
    name = "synthesis"
    description = "Synthesizing final analysis"
    default_timeout = 600  # Many LLM calls for files + functions + synthesis

    async def execute(self) -> dict:
        import asyncio
        from backend.analysis.prompts import (
            SYSTEM_PROMPT, master_synthesis_prompt, recommendation_prompt,
            file_analysis_prompt, function_analysis_prompt,
            dependency_analysis_prompt,
        )
        from backend.llm.model_router import model_router
        from backend.graphs.call_graph import ImpactAnalyzer
        from pathlib import Path

        parsed_files = await self.memory.get("parsed.files", [])
        overview = await self.memory.get("analysis.repo_overview", {})
        tech_stack = await self.memory.get("analysis.tech_stack", {})
        modules = await self.memory.get("analysis.modules", [])
        system_flow = await self.memory.get("analysis.system_flow", {})
        health = await self.memory.get("analysis.health_dashboard", {})
        security = await self.memory.get("analysis.security_analysis", {})
        production = await self.memory.get("analysis.production_readiness", {})
        dep_data = await self.memory.get("graphs.dependency", {})
        call_data = await self.memory.get("graphs.call", {})

        # File analysis (batched, top 20 important files)
        await self.emit_progress("Analyzing key files")
        entry_names = {"main", "app", "index", "server", "manage", "cli", "run", "__main__"}
        sorted_files = sorted(
            parsed_files,
            key=lambda pf: 0 if Path(pf["file_path"]).stem.lower() in entry_names else 5,
        )
        lmm_files = [pf for pf in sorted_files if not any(
            pat in pf["file_path"].lower()
            for pat in ["fixtures/", "mock", "setup.py", "migrations/", ".d.ts"]
        )]

        impact_analyzer = ImpactAnalyzer()
        impact_analyzer.set_graphs(dep_data, call_data)
        sem = asyncio.Semaphore(6)

        async def _analyze_file(pf):
            async with sem:
                fr = await model_router.generate_json(
                    "file_analysis",
                    file_analysis_prompt(pf["file_path"], pf["source_preview"]),
                    system_prompt=SYSTEM_PROMPT,
                )
                fr["file_path"] = pf["file_path"]
                impact = impact_analyzer.analyze_file_impact(pf["file_path"], parsed_files, modules)
                fr["importance"] = impact["importance"]
                fr["risk_level"] = impact["risk_level"]
                fr["dependent_count"] = len(impact["direct_dependents"]) + len(impact["indirect_dependents"])
                return fr

        file_results = await asyncio.gather(
            *[_analyze_file(pf) for pf in lmm_files[:10]],
            return_exceptions=True,
        )
        file_analyses = [r for r in file_results if not isinstance(r, Exception)]

        # Function analysis (top 30 functions)
        await self.emit_progress("Analyzing key functions")
        all_functions = []
        for pf in lmm_files:
            for func in pf["functions"]:
                all_functions.append(func)

        async def _analyze_func(func):
            async with sem:
                fr = await model_router.generate_json(
                    "function_analysis",
                    function_analysis_prompt(func["name"], func["body"]),
                    system_prompt=SYSTEM_PROMPT,
                )
                fr["function_name"] = func["name"]
                fr["file_path"] = func["file_path"]
                return fr

        func_results = await asyncio.gather(
            *[_analyze_func(f) for f in all_functions[:15]],
            return_exceptions=True,
        )
        function_analyses = [r for r in func_results if not isinstance(r, Exception)]

        # Dependencies LLM
        await self.emit_progress("Deep dependency analysis")
        try:
            dep_context = json.dumps(dep_data, indent=2)
            dependencies = await model_router.generate_json(
                "dependencies",
                dependency_analysis_prompt(truncate(dep_context, 4000)),
                system_prompt=SYSTEM_PROMPT,
            )
            dependencies["graph_data"] = dep_data
        except Exception as e:
            dependencies = {"error": str(e), "graph_data": dep_data}

        # Recommendations
        await self.emit_progress("Generating recommendations")
        try:
            rec_context = json.dumps({
                "repo_overview": overview,
                "tech_stack": tech_stack,
                "modules": modules,
                "health_dashboard": health,
                "security": security,
                "production_readiness": production,
            }, indent=2)
            rec_result = await model_router.generate_json(
                "recommendations",
                recommendation_prompt(truncate(rec_context, 5000)),
                system_prompt=SYSTEM_PROMPT,
            )
            if isinstance(rec_result, dict) and "recommendations" in rec_result:
                recommendations = rec_result["recommendations"]
            elif isinstance(rec_result, list):
                recommendations = rec_result
            else:
                recommendations = [rec_result]
        except Exception as e:
            recommendations = [{"error": str(e)}]

        # Master synthesis
        await self.emit_progress("Creating final synthesis")
        try:
            synthesis_context = json.dumps({
                "repo_overview": overview,
                "tech_stack": tech_stack,
                "modules": modules,
                "system_flow": system_flow,
                "health_scores": {
                    "overall": health.get("overall_score") if health else None,
                    "code_quality": (health.get("code_quality", {}) or {}).get("score"),
                    "production": (health.get("production_readiness", {}) or {}).get("score"),
                    "security": (health.get("security", {}) or {}).get("score"),
                    "scalability": (health.get("scalability", {}) or {}).get("score"),
                } if health else {},
                "production_readiness": production,
                "security": security,
            }, indent=2)
            master_synthesis = await model_router.generate_json(
                "synthesis",
                master_synthesis_prompt(truncate(synthesis_context, 5000)),
                system_prompt=SYSTEM_PROMPT,
            )
        except Exception as e:
            master_synthesis = {"error": str(e)}

        await self.memory.update({
            "analysis.file_analyses": file_analyses,
            "analysis.function_analyses": function_analyses,
            "analysis.dependencies": dependencies,
            "analysis.recommendations": recommendations,
            "analysis.master_synthesis": master_synthesis,
        })

        return {"master_synthesis": master_synthesis}
