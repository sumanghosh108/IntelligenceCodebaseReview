"""Multi-pass analysis engine orchestrating the entire pipeline."""
import json
import logging
from pathlib import Path

from backend.analysis.prompts import (
    SYSTEM_PROMPT, repo_overview_prompt, tech_stack_prompt,
    module_identification_prompt, file_analysis_prompt, function_analysis_prompt,
    dependency_analysis_prompt, system_flow_prompt, flow_diagram_prompt,
    production_readiness_prompt, security_analysis_prompt, cost_analysis_prompt,
    interview_explainer_prompt, master_synthesis_prompt,
)
from backend.llm.ollama_client import ollama_client
from backend.embeddings.vector_store import vector_store
from backend.parsers.code_parser import CodeParser
from backend.core.repo_manager import RepoManager
from backend.graphs.dependency_graph import DependencyGraphBuilder
from backend.models.schemas import AnalysisResult, AnalysisStatus
from backend.utils.helpers import cache, truncate

logger = logging.getLogger(__name__)


class AnalysisEngine:
    def __init__(self):
        self.parser = CodeParser()
        self.repo_manager = RepoManager()
        self.graph_builder = DependencyGraphBuilder()

    async def analyze_repo(self, repo_url: str, branch: str = "main") -> AnalysisResult:
        result = AnalysisResult(repo_url=repo_url, status=AnalysisStatus.CLONING)

        try:
            # Step 1: Clone
            logger.info(f"Cloning {repo_url}...")
            repo_path = self.repo_manager.clone(repo_url, branch)

            # Step 2: Parse
            result.status = AnalysisStatus.PARSING
            logger.info("Parsing codebase...")
            files = self.repo_manager.list_files(repo_path)
            parsed_files = self.parser.parse_repo(repo_path, files)

            # Step 3: Embed
            result.status = AnalysisStatus.EMBEDDING
            logger.info("Embedding code chunks...")
            collection_name = f"repo_{hash(repo_url) % 100000}"
            vector_store.delete_collection(collection_name)
            all_chunks = []
            for pf in parsed_files:
                all_chunks.extend(pf["chunks"])
            if all_chunks:
                vector_store.embed_chunks(all_chunks, collection_name)

            # Step 4: Multi-pass analysis
            result.status = AnalysisStatus.ANALYZING
            logger.info("Running multi-pass analysis...")

            # Gather context
            config_files = self.repo_manager.get_config_files(repo_path)
            folder_structure = self.repo_manager.get_folder_structure(repo_path)

            config_context = "\n\n".join(
                f"--- {name} ---\n{content}" for name, content in config_files.items()
            )
            structure_context = json.dumps(folder_structure, indent=2)

            # Build file summary
            file_summary = []
            for pf in parsed_files[:50]:
                funcs = [f["name"] for f in pf["functions"]]
                file_summary.append(
                    f"  {pf['file_path']} ({pf['language']}, {pf['line_count']} lines) "
                    f"- functions: {funcs}"
                )
            file_summary_str = "\n".join(file_summary)

            overview_context = (
                f"Config files:\n{truncate(config_context, 3000)}\n\n"
                f"Folder structure:\n{truncate(structure_context, 2000)}\n\n"
                f"Files:\n{truncate(file_summary_str, 2000)}"
            )

            # Pass 1: Repo Overview
            logger.info("Pass 1: Repo overview...")
            result.repo_overview = await self._llm_analyze(
                repo_overview_prompt(overview_context)
            )

            # Pass 2: Tech Stack
            logger.info("Pass 2: Tech stack...")
            result.tech_stack = await self._llm_analyze(
                tech_stack_prompt(config_context)
            )

            # Pass 3: Module Identification
            logger.info("Pass 3: Module identification...")
            modules_raw = await self._llm_analyze(
                module_identification_prompt(structure_context)
            )
            if isinstance(modules_raw, list):
                result.modules = modules_raw
            elif isinstance(modules_raw, dict) and "raw_response" not in modules_raw:
                result.modules = [modules_raw]
            else:
                result.modules = [modules_raw] if modules_raw else []

            # Pass 4: File Analysis (top 20 files)
            logger.info("Pass 4: File analysis...")
            result.file_analyses = []
            for pf in parsed_files[:20]:
                file_result = await self._llm_analyze(
                    file_analysis_prompt(pf["file_path"], pf["source_preview"])
                )
                file_result["file_path"] = pf["file_path"]
                result.file_analyses.append(file_result)

            # Pass 5: Function Analysis (top 30 functions)
            logger.info("Pass 5: Function analysis...")
            result.function_analyses = []
            all_functions = []
            for pf in parsed_files:
                for func in pf["functions"]:
                    all_functions.append(func)
            for func in all_functions[:30]:
                func_result = await self._llm_analyze(
                    function_analysis_prompt(func["name"], func["body"])
                )
                func_result["function_name"] = func["name"]
                func_result["file_path"] = func["file_path"]
                result.function_analyses.append(func_result)

            # Pass 6: Dependency Graph
            logger.info("Pass 6: Dependency analysis...")
            dep_data = self.graph_builder.build_from_parsed(parsed_files)
            dep_context = json.dumps(dep_data, indent=2)
            result.dependencies = await self._llm_analyze(
                dependency_analysis_prompt(dep_context)
            )
            result.dependencies["graph_data"] = dep_data

            # Pass 7: System Flow
            logger.info("Pass 7: System flow...")
            flow_context = (
                f"Repo overview: {json.dumps(result.repo_overview)}\n\n"
                f"Modules: {json.dumps(result.modules)}\n\n"
                f"Files summary:\n{file_summary_str}"
            )
            result.system_flow = await self._llm_analyze(
                system_flow_prompt(truncate(flow_context, 4000))
            )

            # Pass 8: Flow Diagram (Mermaid)
            logger.info("Pass 8: Flow diagram...")
            diagram_context = (
                f"Modules: {json.dumps(result.modules)}\n\n"
                f"System flow: {json.dumps(result.system_flow)}"
            )
            diagram_raw = await ollama_client.generate(
                flow_diagram_prompt(truncate(diagram_context, 3000)),
                system_prompt=SYSTEM_PROMPT,
            )
            # Clean mermaid output
            diagram = diagram_raw.strip()
            if diagram.startswith("```"):
                lines = diagram.splitlines()
                lines = [l for l in lines if not l.strip().startswith("```")]
                diagram = "\n".join(lines)
            result.flow_diagram = diagram

            # Pass 9: Production Readiness
            logger.info("Pass 9: Production readiness...")
            result.production_readiness = await self._llm_analyze(
                production_readiness_prompt(overview_context)
            )

            # Pass 10: Security Analysis
            logger.info("Pass 10: Security analysis...")
            security_context = overview_context
            # Add some actual code samples for security review
            code_samples = []
            for pf in parsed_files[:10]:
                code_samples.append(f"--- {pf['file_path']} ---\n{pf['source_preview']}")
            security_context += "\n\nCode samples:\n" + truncate("\n".join(code_samples), 3000)
            result.security_analysis = await self._llm_analyze(
                security_analysis_prompt(security_context)
            )

            # Pass 11: Cost Analysis
            logger.info("Pass 11: Cost analysis...")
            result.cost_analysis = await self._llm_analyze(
                cost_analysis_prompt(config_context)
            )

            # Pass 12: Interview Explainer
            logger.info("Pass 12: Interview explainer...")
            interview_context = (
                f"Overview: {json.dumps(result.repo_overview)}\n"
                f"Tech: {json.dumps(result.tech_stack)}\n"
                f"Modules: {json.dumps(result.modules)}\n"
                f"Flow: {json.dumps(result.system_flow)}"
            )
            result.interview_explainer = await self._llm_analyze(
                interview_explainer_prompt(truncate(interview_context, 4000))
            )

            # Pass 13: Master Synthesis
            logger.info("Pass 13: Master synthesis...")
            synthesis_context = json.dumps({
                "repo_overview": result.repo_overview,
                "tech_stack": result.tech_stack,
                "modules": result.modules,
                "system_flow": result.system_flow,
                "production_readiness": result.production_readiness,
                "security": result.security_analysis,
            }, indent=2)
            result.master_synthesis = await self._llm_analyze(
                master_synthesis_prompt(truncate(synthesis_context, 5000))
            )

            result.status = AnalysisStatus.COMPLETED
            logger.info("Analysis completed!")

        except ConnectionError as e:
            result.status = AnalysisStatus.FAILED
            result.errors.append(str(e))
            logger.error(f"Connection error: {e}")
        except Exception as e:
            result.status = AnalysisStatus.FAILED
            result.errors.append(str(e))
            logger.error(f"Analysis failed: {e}", exc_info=True)

        return result

    async def _llm_analyze(self, prompt: str) -> dict:
        return await ollama_client.generate_json(prompt, system_prompt=SYSTEM_PROMPT)

    async def query_codebase(self, question: str, collection_name: str) -> dict:
        """RAG-based query: retrieve relevant chunks then ask LLM."""
        relevant = vector_store.query(question, n_results=5, collection_name=collection_name)

        context_parts = []
        for r in relevant:
            meta = r["metadata"]
            context_parts.append(
                f"--- {meta['file_path']} (lines {meta['start_line']}-{meta['end_line']}) ---\n"
                f"{r['content']}"
            )
        context = "\n\n".join(context_parts)

        prompt = f"""Answer the following question about the codebase using ONLY the provided context.

Question: {question}

Context:
{context}

Respond in JSON:
{{
  "answer": "",
  "relevant_files": [],
  "confidence": "high/medium/low"
}}"""

        result = await self._llm_analyze(prompt)
        result["sources"] = [r["metadata"] for r in relevant]
        return result
