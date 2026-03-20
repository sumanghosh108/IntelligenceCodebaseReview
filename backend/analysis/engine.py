"""Multi-pass analysis engine with progressive output, parallel processing, and caching.

Architecture:
- Phase 1 (Fast ~5s): Clone + parse → quick stats (repo name, languages, file count)
- Phase 2 (Medium ~15s): Deterministic passes → health scores, graphs, knowledge graph
- Phase 3 (LLM ~30s): Overview, tech stack, modules (hybrid model routing + CoT)
- Phase 4 (Background): Deep file/function analysis, all remaining passes

Smart optimizations:
- Hybrid model routing (fast/code/deep models per task)
- Chain-of-Thought reasoning for deep analysis (extract→validate→insight)
- Code Knowledge Graph (unified file/function/class/module relationships)
- Parallel LLM calls for independent passes
- Full result caching (memory + disk with TTL)
- Progressive result updates (frontend can poll and show partial results)
"""
import asyncio
import json
import logging
import time
from pathlib import Path

from backend.analysis.prompts import (
    SYSTEM_PROMPT, repo_overview_prompt, tech_stack_prompt,
    module_identification_prompt, file_analysis_prompt, function_analysis_prompt,
    dependency_analysis_prompt, system_flow_prompt, flow_diagram_prompt,
    production_readiness_prompt, security_analysis_prompt, cost_analysis_prompt,
    interview_explainer_prompt, master_synthesis_prompt,
    recommendation_prompt, abstraction_views_prompt, impact_analysis_llm_prompt,
    threat_model_prompt, auto_doc_prompt, failure_analysis_prompt,
)
from backend.llm.ollama_client import ollama_client
from backend.llm.model_router import model_router
from backend.llm.chain_of_thought import cot_pipeline
from backend.embeddings.vector_store import vector_store
from backend.embeddings.hybrid_search import HybridSearchEngine
from backend.parsers.code_parser import CodeParser
from backend.core.repo_manager import RepoManager
from backend.graphs.dependency_graph import DependencyGraphBuilder
from backend.graphs.call_graph import CallGraphBuilder, ImpactAnalyzer
from backend.graphs.knowledge_graph import CodeKnowledgeGraph
from backend.scoring.health_scorer import HealthScorer
from backend.scoring.code_quality_analyzer import CodeQualityAnalyzer
from backend.analysis.advanced_analyzers import (
    APIContractDetector, DatabaseSchemaDetector, PerformanceDetector,
    ComplexityScorer, ArchitectureDetector, SecuritySmellDetector,
    FailureModePredictor,
)
from backend.analysis.timeline import TimelineAnalyzer
from backend.models.schemas import AnalysisResult, AnalysisStatus
from backend.utils.helpers import cache, truncate, collection_name_for
from config.settings import settings

logger = logging.getLogger(__name__)

# Files to deprioritize for LLM analysis (still parsed for structure)
SKIP_PATTERNS_FOR_LLM = [
    "fixtures/", "mock", "setup.py", "setup.cfg",
    "migrations/", "alembic/", ".d.ts", "types.ts",
]


def _is_test_file(file_path: str) -> bool:
    """Check if a file is a test file."""
    fp_lower = file_path.lower()
    test_patterns = [
        "test_", "_test.", ".test.", ".spec.", "tests/", "test/", "__tests__/",
        "spec/", "conftest",
    ]
    return any(pat in fp_lower for pat in test_patterns)


def _is_test_or_low_priority(file_path: str) -> bool:
    """Check if a file should be deprioritized for LLM analysis (non-test low-priority files)."""
    fp_lower = file_path.lower()
    return any(pat in fp_lower for pat in SKIP_PATTERNS_FOR_LLM)


def _sort_files_by_importance(parsed_files: list[dict]) -> list[dict]:
    """Sort files: entry points first, then by size/connections, tests last."""
    entry_names = {"main", "app", "index", "server", "manage", "cli", "run", "__main__"}
    config_names = {"config", "settings", "constants", "env"}

    def score(pf):
        fp = pf["file_path"].lower()
        stem = Path(fp).stem.lower()

        # Entry points get top priority
        if stem in entry_names:
            return 0
        # Config files are important
        if stem in config_names:
            return 1
        # Routes/API endpoints
        if any(kw in fp for kw in ["route", "api", "endpoint", "view", "controller", "handler"]):
            return 2
        # Models/schemas
        if any(kw in fp for kw in ["model", "schema", "entity"]):
            return 3
        # Core business logic (by function count)
        if len(pf["functions"]) > 3:
            return 4
        # Test files — analyzed but lower priority
        if _is_test_file(fp):
            return 7
        # Other low-priority (fixtures, migrations, etc.)
        if _is_test_or_low_priority(fp):
            return 9
        return 5

    return sorted(parsed_files, key=score)


class AnalysisEngine:
    # All progress steps with labels
    PROGRESS_STEPS = [
        ("cloning", "Cloning repository"),
        ("parsing", "Parsing source files"),
        ("quick_stats", "Generating quick stats"),
        ("embedding", "Embedding code chunks"),
        ("health_scoring", "Scoring code health"),
        ("dependency_graph", "Building dependency graph"),
        ("call_graph", "Building call graph"),
        ("knowledge_graph", "Building knowledge graph"),
        ("code_quality", "Analyzing code quality"),
        ("api_contracts", "Detecting API contracts"),
        ("db_schema", "Detecting database schema"),
        ("perf_analysis", "Detecting performance bottlenecks"),
        ("complexity", "Computing complexity score"),
        ("arch_patterns", "Detecting architecture patterns"),
        ("security_smells", "Scanning security threats"),
        ("timeline", "Analyzing git timeline"),
        ("overview", "Analyzing repository overview"),
        ("tech_stack", "Detecting tech stack"),
        ("modules", "Identifying modules"),
        ("file_analysis", "Analyzing key files"),
        ("function_analysis", "Analyzing key functions"),
        ("dependencies_llm", "Deep dependency analysis"),
        ("system_flow", "Tracing system flow"),
        ("flow_diagram", "Generating flow diagram"),
        ("production", "Checking production readiness"),
        ("security", "Running security analysis"),
        ("cost", "Analyzing costs"),
        ("interview", "Generating interview guide"),
        ("views", "Creating abstraction views"),
        ("recommendations", "Generating recommendations"),
        ("threat_model", "Security threat modeling"),
        ("auto_docs", "Generating documentation"),
        ("failure_analysis", "Predicting failure modes"),
        ("synthesis", "Final synthesis"),
    ]

    # Tasks that use Chain-of-Thought (multi-step reasoning)
    COT_TASKS = set(settings.cot_tasks.split(","))

    def __init__(self):
        self.parser = CodeParser()
        self.repo_manager = RepoManager()
        self.graph_builder = DependencyGraphBuilder()
        self.call_graph_builder = CallGraphBuilder()
        self.knowledge_graph_builder = CodeKnowledgeGraph()
        self.health_scorer = HealthScorer()
        self.quality_analyzer = CodeQualityAnalyzer()
        self.api_detector = APIContractDetector()
        self.db_detector = DatabaseSchemaDetector()
        self.perf_detector = PerformanceDetector()
        self.complexity_scorer = ComplexityScorer()
        self.arch_detector = ArchitectureDetector()
        self.security_smell_detector = SecuritySmellDetector()
        self.failure_predictor = FailureModePredictor()
        self.timeline_analyzer = TimelineAnalyzer()
        self.impact_analyzer = ImpactAnalyzer()
        # Caches
        self._parsed_cache: dict[str, list[dict]] = {}
        self._dep_cache: dict[str, dict] = {}
        self._call_cache: dict[str, dict] = {}
        self._modules_cache: dict[str, list[dict]] = {}
        self._result_cache: dict[str, AnalysisResult] = {}
        self._hybrid_search_cache: dict[str, HybridSearchEngine] = {}

    def _init_progress(self, result: AnalysisResult):
        """Initialize all progress steps as pending."""
        result.progress_steps = [
            {"phase": phase, "label": label, "status": "pending", "duration_ms": None}
            for phase, label in self.PROGRESS_STEPS
        ]

    def _update_step(self, result: AnalysisResult, phase: str, status: str, duration_ms: int = None):
        """Update a progress step status."""
        result.current_phase = phase
        for step in result.progress_steps:
            if step["phase"] == phase:
                step["status"] = status
                if duration_ms is not None:
                    step["duration_ms"] = duration_ms
                break

    def _record_stage_error(self, result: AnalysisResult, phase: str, error: str):
        """Record an error for a specific stage without stopping the pipeline."""
        from datetime import datetime, timezone
        result.stage_errors.append({
            "phase": phase,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Mark the step as failed
        for step in result.progress_steps:
            if step["phase"] == phase:
                step["status"] = "failed"
                break

    async def analyze_repo(
        self,
        repo_url: str,
        branch: str = "main",
        result_ref: AnalysisResult = None,
    ) -> AnalysisResult:
        """Run full progressive analysis.

        If result_ref is provided, updates are written to it in-place so the
        status polling endpoint always sees the latest state.
        """
        # Check in-memory cache first, then disk cache with TTL
        cache_key = f"{repo_url}@{branch}"
        cached_result = None

        if cache_key in self._result_cache:
            cached_result = self._result_cache[cache_key]
        else:
            # Check disk cache with TTL
            disk_cached = cache.get_with_ttl("result", cache_key, settings.result_cache_ttl)
            if disk_cached:
                try:
                    cached_result = AnalysisResult(**disk_cached)
                except Exception:
                    cached_result = None

        if cached_result and cached_result.status == AnalysisStatus.COMPLETED:
            logger.info(f"Cache hit for {repo_url} (TTL={settings.result_cache_ttl}s)")
            if result_ref:
                # Copy cached fields but preserve the new job_id
                new_job_id = result_ref.job_id
                new_created = result_ref.created_at
                for field in cached_result.model_fields:
                    setattr(result_ref, field, getattr(cached_result, field))
                result_ref.job_id = new_job_id
                result_ref.created_at = new_created
            self._result_cache[cache_key] = cached_result
            return result_ref or cached_result

        from datetime import datetime, timezone
        import uuid

        result = result_ref or AnalysisResult(repo_url=repo_url, status=AnalysisStatus.CLONING)
        if not result.job_id:
            result.job_id = str(uuid.uuid4())
        result.branch = branch
        result.created_at = datetime.now(timezone.utc).isoformat()
        self._init_progress(result)

        try:
            # ============================================
            # PHASE 1: FAST (~5 sec) — Clone + Parse + Quick Stats
            # ============================================

            # Step: Clone
            t0 = time.monotonic()
            self._update_step(result, "cloning", "running")
            result.status = AnalysisStatus.CLONING
            logger.info(f"Cloning {repo_url}...")
            repo_path = self.repo_manager.clone(repo_url, branch)
            self._update_step(result, "cloning", "done", _ms(t0))

            # Step: Parse
            t0 = time.monotonic()
            self._update_step(result, "parsing", "running")
            result.status = AnalysisStatus.PARSING
            logger.info("Parsing codebase...")
            files = self.repo_manager.list_files(repo_path)
            parsed_files = self.parser.parse_repo(repo_path, files)
            self._update_step(result, "parsing", "done", _ms(t0))

            # Step: Quick stats (available immediately)
            t0 = time.monotonic()
            self._update_step(result, "quick_stats", "running")
            repo_name = repo_url.rstrip("/").split("/")[-1]
            languages = list(set(pf["language"] for pf in parsed_files if pf["language"] != "unknown"))
            total_lines = sum(pf["line_count"] for pf in parsed_files)
            total_functions = sum(len(pf["functions"]) for pf in parsed_files)
            result.quick_stats = {
                "repo_name": repo_name,
                "total_files": len(parsed_files),
                "total_lines": total_lines,
                "total_functions": total_functions,
                "languages": languages,
                "branch": branch,
            }
            self._update_step(result, "quick_stats", "done", _ms(t0))

            # Sort files by importance for LLM analysis
            sorted_files = _sort_files_by_importance(parsed_files)

            # ============================================
            # PHASE 2: DETERMINISTIC (~10 sec) — Health, Graphs, Embedding
            # ============================================

            # Gather context (needed by multiple passes)
            config_files = self.repo_manager.get_config_files(repo_path)
            folder_structure = self.repo_manager.get_folder_structure(repo_path)
            config_context = "\n\n".join(
                f"--- {name} ---\n{content}" for name, content in config_files.items()
            )
            structure_context = json.dumps(folder_structure, indent=2)

            # Build file summary (skip test files)
            important_files = [pf for pf in sorted_files if not _is_test_or_low_priority(pf["file_path"])]
            file_summary = []
            for pf in important_files[:50]:
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

            # Run deterministic passes in parallel
            result.status = AnalysisStatus.EMBEDDING

            async def _embed():
                t = time.monotonic()
                self._update_step(result, "embedding", "running")
                collection_name = collection_name_for(repo_url)
                all_chunks = []
                for pf in parsed_files:
                    all_chunks.extend(pf["chunks"])
                if all_chunks:
                    content_hash = vector_store.compute_content_hash(all_chunks)
                    vector_store.embed_chunks(
                        all_chunks, collection_name, content_hash=content_hash
                    )
                    # Build hybrid search index (BM25 + vector)
                    hybrid = HybridSearchEngine(vector_store, collection_name)
                    hybrid.build_index(all_chunks)
                    self._hybrid_search_cache[repo_url] = hybrid
                    logger.info("Hybrid search index (BM25 + vector) built")
                self._update_step(result, "embedding", "done", _ms(t))

            async def _health():
                t = time.monotonic()
                self._update_step(result, "health_scoring", "running")
                result.health_dashboard = self.health_scorer.score_all(
                    parsed_files, config_files, folder_structure
                )
                self._update_step(result, "health_scoring", "done", _ms(t))

            async def _dep_graph():
                t = time.monotonic()
                self._update_step(result, "dependency_graph", "running")
                dep_data = self.graph_builder.build_from_parsed(parsed_files)
                self._dep_cache[repo_url] = dep_data
                self._update_step(result, "dependency_graph", "done", _ms(t))
                return dep_data

            async def _call_graph():
                t = time.monotonic()
                self._update_step(result, "call_graph", "running")
                call_data = self.call_graph_builder.build(parsed_files)
                result.call_graph = call_data
                self._call_cache[repo_url] = call_data
                self._update_step(result, "call_graph", "done", _ms(t))
                return call_data

            # Run embedding, health, dep graph, call graph in parallel
            embed_task = asyncio.create_task(_embed())
            health_task = asyncio.create_task(_health())
            dep_task = asyncio.create_task(_dep_graph())
            call_task = asyncio.create_task(_call_graph())

            dep_data, call_data = await asyncio.gather(dep_task, call_task)
            await asyncio.gather(embed_task, health_task)

            # Build knowledge graph
            t0 = time.monotonic()
            self._update_step(result, "knowledge_graph", "running")
            try:
                kg_summary = self.knowledge_graph_builder.build(parsed_files, dep_data, call_data)
                result.knowledge_graph = {
                    "summary": kg_summary,
                    "hotspots": self.knowledge_graph_builder.get_hotspots(10),
                    "module_interactions": self.knowledge_graph_builder.get_module_interactions(),
                }
                self._update_step(result, "knowledge_graph", "done", _ms(t0))
            except Exception as e:
                self._record_stage_error(result, "knowledge_graph", str(e))
                logger.error(f"Knowledge graph failed: {e}")

            # Code Quality Intelligence (rule-based + AI hybrid)
            t0 = time.monotonic()
            self._update_step(result, "code_quality", "running")
            try:
                rule_issues = self.quality_analyzer.analyze_rule_based(parsed_files)
                logger.info(f"Rule-based quality: {len(rule_issues)} issues found")

                # AI architecture/design critique
                ai_issues = []
                try:
                    ai_prompt = self.quality_analyzer.build_ai_prompt(parsed_files, rule_issues)
                    ai_raw = await model_router.generate_json(
                        "code_quality", ai_prompt, system_prompt=SYSTEM_PROMPT
                    )
                    if isinstance(ai_raw, list):
                        ai_issues = ai_raw
                    elif isinstance(ai_raw, dict) and "issues" in ai_raw:
                        ai_issues = ai_raw["issues"]
                    elif isinstance(ai_raw, dict) and "raw_response" not in ai_raw:
                        ai_issues = [ai_raw]
                except Exception as e:
                    logger.warning(f"AI quality critique failed (rule-based still available): {e}")

                result.code_quality = self.quality_analyzer.merge_results(rule_issues, ai_issues)
                self._update_step(result, "code_quality", "done", _ms(t0))
            except Exception as e:
                self._record_stage_error(result, "code_quality", str(e))
                logger.error(f"Code quality analysis failed: {e}")

            # --- Advanced Deterministic Analyzers (all run in parallel) ---
            async def _api_contracts():
                t = time.monotonic()
                self._update_step(result, "api_contracts", "running")
                try:
                    result.api_contracts = self.api_detector.detect(parsed_files, config_files)
                    self._update_step(result, "api_contracts", "done", _ms(t))
                except Exception as e:
                    self._record_stage_error(result, "api_contracts", str(e))

            async def _db_schema():
                t = time.monotonic()
                self._update_step(result, "db_schema", "running")
                try:
                    result.db_schema = self.db_detector.detect(parsed_files, config_files)
                    self._update_step(result, "db_schema", "done", _ms(t))
                except Exception as e:
                    self._record_stage_error(result, "db_schema", str(e))

            async def _perf():
                t = time.monotonic()
                self._update_step(result, "perf_analysis", "running")
                try:
                    result.perf_bottlenecks = self.perf_detector.detect(parsed_files)
                    self._update_step(result, "perf_analysis", "done", _ms(t))
                except Exception as e:
                    self._record_stage_error(result, "perf_analysis", str(e))

            async def _complexity():
                t = time.monotonic()
                self._update_step(result, "complexity", "running")
                try:
                    result.complexity_score = self.complexity_scorer.score(parsed_files, dep_data)
                    self._update_step(result, "complexity", "done", _ms(t))
                except Exception as e:
                    self._record_stage_error(result, "complexity", str(e))

            async def _arch():
                t = time.monotonic()
                self._update_step(result, "arch_patterns", "running")
                try:
                    result.architecture_patterns = self.arch_detector.detect(
                        parsed_files, folder_structure, config_files
                    )
                    self._update_step(result, "arch_patterns", "done", _ms(t))
                except Exception as e:
                    self._record_stage_error(result, "arch_patterns", str(e))

            async def _sec_smells():
                t = time.monotonic()
                self._update_step(result, "security_smells", "running")
                try:
                    result.security_threats = self.security_smell_detector.detect(parsed_files)
                    self._update_step(result, "security_smells", "done", _ms(t))
                except Exception as e:
                    self._record_stage_error(result, "security_smells", str(e))

            async def _timeline():
                t = time.monotonic()
                self._update_step(result, "timeline", "running")
                try:
                    result.timeline = self.timeline_analyzer.analyze(repo_path)
                    self._update_step(result, "timeline", "done", _ms(t))
                except Exception as e:
                    self._record_stage_error(result, "timeline", str(e))

            await asyncio.gather(
                asyncio.create_task(_api_contracts()),
                asyncio.create_task(_db_schema()),
                asyncio.create_task(_perf()),
                asyncio.create_task(_complexity()),
                asyncio.create_task(_arch()),
                asyncio.create_task(_sec_smells()),
                asyncio.create_task(_timeline()),
            )

            # Setup impact analyzer
            self.impact_analyzer.set_graphs(dep_data, call_data)
            self._parsed_cache[repo_url] = parsed_files

            # ============================================
            # PHASE 3: LLM FAST PASSES (~30 sec) — Overview, Tech, Modules
            # ============================================
            result.status = AnalysisStatus.ANALYZING

            # Run overview + tech stack in parallel (independent)
            async def _overview():
                t = time.monotonic()
                self._update_step(result, "overview", "running")
                try:
                    result.repo_overview = await self._llm_analyze(
                        repo_overview_prompt(overview_context),
                        task="overview", code_context=overview_context,
                    )
                    self._update_step(result, "overview", "done", _ms(t))
                except Exception as e:
                    self._record_stage_error(result, "overview", str(e))
                    logger.error(f"Overview failed: {e}")

            async def _tech():
                t = time.monotonic()
                self._update_step(result, "tech_stack", "running")
                try:
                    result.tech_stack = await self._llm_analyze(
                        tech_stack_prompt(config_context),
                        task="tech_stack",
                    )
                    self._update_step(result, "tech_stack", "done", _ms(t))
                except Exception as e:
                    self._record_stage_error(result, "tech_stack", str(e))
                    logger.error(f"Tech stack failed: {e}")

            await asyncio.gather(
                asyncio.create_task(_overview()),
                asyncio.create_task(_tech()),
            )

            # Modules (depends on folder structure only)
            t0 = time.monotonic()
            self._update_step(result, "modules", "running")
            try:
                modules_raw = await self._llm_analyze(
                    module_identification_prompt(structure_context),
                    task="modules",
                )
                if isinstance(modules_raw, list):
                    result.modules = modules_raw
                elif isinstance(modules_raw, dict) and "raw_response" not in modules_raw:
                    result.modules = [modules_raw]
                else:
                    result.modules = [modules_raw] if modules_raw else []
                self._modules_cache[repo_url] = result.modules
                self._update_step(result, "modules", "done", _ms(t0))
            except Exception as e:
                self._record_stage_error(result, "modules", str(e))
                result.modules = []
                logger.error(f"Modules failed: {e}")

            # ============================================
            # PHASE 4: DEEP ANALYSIS (background, ~2-5 min)
            # ============================================

            # File Analysis — batched parallel LLM calls (max 3 concurrent)
            t0 = time.monotonic()
            self._update_step(result, "file_analysis", "running")
            result.file_analyses = []
            lmm_files = [pf for pf in sorted_files if not _is_test_or_low_priority(pf["file_path"]) or _is_test_file(pf["file_path"])]
            try:
                sem = asyncio.Semaphore(settings.llm_concurrency)

                async def _analyze_file(pf):
                    async with sem:
                        fr = await self._llm_analyze(
                            file_analysis_prompt(pf["file_path"], pf["source_preview"]),
                            task="file_analysis", code_context=pf["source_preview"],
                        )
                        fr["file_path"] = pf["file_path"]
                        impact = self.impact_analyzer.analyze_file_impact(
                            pf["file_path"], parsed_files, result.modules
                        )
                        fr["importance"] = impact["importance"]
                        fr["risk_level"] = impact["risk_level"]
                        fr["dependent_count"] = len(impact["direct_dependents"]) + len(impact["indirect_dependents"])
                        return fr

                file_results = await asyncio.gather(
                    *[_analyze_file(pf) for pf in lmm_files[:20]],
                    return_exceptions=True,
                )
                for fr in file_results:
                    if isinstance(fr, Exception):
                        logger.warning(f"File analysis item failed: {fr}")
                    else:
                        result.file_analyses.append(fr)
                self._update_step(result, "file_analysis", "done", _ms(t0))
            except Exception as e:
                self._record_stage_error(result, "file_analysis", str(e))
                logger.error(f"File analysis failed: {e}")

            # Function Analysis — batched parallel LLM calls (max 3 concurrent)
            t0 = time.monotonic()
            self._update_step(result, "function_analysis", "running")
            result.function_analyses = []
            try:
                all_functions = []
                for pf in lmm_files:
                    for func in pf["functions"]:
                        all_functions.append(func)

                async def _analyze_func(func):
                    async with sem:
                        fr = await self._llm_analyze(
                            function_analysis_prompt(func["name"], func["body"]),
                            task="function_analysis", code_context=func["body"],
                        )
                        fr["function_name"] = func["name"]
                        fr["file_path"] = func["file_path"]
                        return fr

                func_results = await asyncio.gather(
                    *[_analyze_func(f) for f in all_functions[:30]],
                    return_exceptions=True,
                )
                for fr in func_results:
                    if isinstance(fr, Exception):
                        logger.warning(f"Function analysis item failed: {fr}")
                    else:
                        result.function_analyses.append(fr)
                self._update_step(result, "function_analysis", "done", _ms(t0))
            except Exception as e:
                self._record_stage_error(result, "function_analysis", str(e))
                logger.error(f"Function analysis failed: {e}")

            # Run Dep LLM + System Flow + Flow Diagram in sequence
            t0 = time.monotonic()
            self._update_step(result, "dependencies_llm", "running")
            try:
                dep_context = json.dumps(dep_data, indent=2)
                result.dependencies = await self._llm_analyze(
                    dependency_analysis_prompt(truncate(dep_context, 4000)),
                    task="dependencies",
                )
                result.dependencies["graph_data"] = dep_data
                self._update_step(result, "dependencies_llm", "done", _ms(t0))
            except Exception as e:
                self._record_stage_error(result, "dependencies_llm", str(e))
                logger.error(f"Dependencies LLM failed: {e}")

            t0 = time.monotonic()
            self._update_step(result, "system_flow", "running")
            try:
                flow_context = (
                    f"Repo overview: {truncate(json.dumps(result.repo_overview), 1000)}\n\n"
                    f"Modules: {truncate(json.dumps(result.modules), 1000)}\n\n"
                    f"Files summary:\n{truncate(file_summary_str, 2000)}"
                )
                result.system_flow = await self._llm_analyze(
                    system_flow_prompt(flow_context),
                    task="system_flow", code_context=flow_context,
                )
                self._update_step(result, "system_flow", "done", _ms(t0))
            except Exception as e:
                self._record_stage_error(result, "system_flow", str(e))
                logger.error(f"System flow failed: {e}")

            t0 = time.monotonic()
            self._update_step(result, "flow_diagram", "running")
            try:
                diagram_context = (
                    f"Modules: {truncate(json.dumps(result.modules), 1500)}\n\n"
                    f"System flow: {truncate(json.dumps(result.system_flow), 1500)}"
                )
                diagram_raw = await model_router.generate(
                    "modules", flow_diagram_prompt(diagram_context),
                    system_prompt=SYSTEM_PROMPT,
                )
                diagram = diagram_raw.strip()
                if diagram.startswith("```"):
                    lines = diagram.splitlines()
                    lines = [l for l in lines if not l.strip().startswith("```")]
                    diagram = "\n".join(lines)
                result.flow_diagram = diagram
                self._update_step(result, "flow_diagram", "done", _ms(t0))
            except Exception as e:
                self._record_stage_error(result, "flow_diagram", str(e))
                logger.error(f"Flow diagram failed: {e}")

            # Run Production + Security + Cost in parallel (independent)
            async def _production():
                t = time.monotonic()
                self._update_step(result, "production", "running")
                try:
                    result.production_readiness = await self._llm_analyze(
                        production_readiness_prompt(overview_context),
                        task="production", code_context=overview_context,
                    )
                    if result.health_dashboard and "production_readiness" in result.health_dashboard:
                        det = result.health_dashboard["production_readiness"]
                        result.production_readiness["deterministic_score"] = det["score"]
                        result.production_readiness["deterministic_details"] = det["details"]
                        result.production_readiness["deterministic_issues"] = det["issues"]
                    self._update_step(result, "production", "done", _ms(t))
                except Exception as e:
                    self._record_stage_error(result, "production", str(e))
                    logger.error(f"Production readiness failed: {e}")

            async def _security():
                t = time.monotonic()
                self._update_step(result, "security", "running")
                try:
                    security_ctx = overview_context
                    code_samples = []
                    for pf in lmm_files[:10]:
                        code_samples.append(f"--- {pf['file_path']} ---\n{pf['source_preview']}")
                    security_ctx += "\n\nCode samples:\n" + truncate("\n".join(code_samples), 3000)
                    result.security_analysis = await self._llm_analyze(
                        security_analysis_prompt(security_ctx),
                        task="security", code_context=security_ctx,
                    )
                    if result.health_dashboard and "security" in result.health_dashboard:
                        det = result.health_dashboard["security"]
                        result.security_analysis["deterministic_score"] = det["score"]
                        result.security_analysis["deterministic_issues"] = det["issues"]
                    self._update_step(result, "security", "done", _ms(t))
                except Exception as e:
                    self._record_stage_error(result, "security", str(e))
                    logger.error(f"Security analysis failed: {e}")

            async def _cost():
                t = time.monotonic()
                self._update_step(result, "cost", "running")
                try:
                    result.cost_analysis = await self._llm_analyze(
                        cost_analysis_prompt(truncate(config_context, 3000)),
                        task="cost",
                    )
                    self._update_step(result, "cost", "done", _ms(t))
                except Exception as e:
                    self._record_stage_error(result, "cost", str(e))
                    logger.error(f"Cost analysis failed: {e}")

            await asyncio.gather(
                asyncio.create_task(_production()),
                asyncio.create_task(_security()),
                asyncio.create_task(_cost()),
            )

            # Run Interview + Abstraction Views in parallel
            async def _interview():
                t = time.monotonic()
                self._update_step(result, "interview", "running")
                try:
                    ctx = (
                        f"Overview: {truncate(json.dumps(result.repo_overview), 1000)}\n"
                        f"Tech: {truncate(json.dumps(result.tech_stack), 800)}\n"
                        f"Modules: {truncate(json.dumps(result.modules), 1000)}\n"
                        f"Flow: {truncate(json.dumps(result.system_flow), 1000)}"
                    )
                    result.interview_explainer = await self._llm_analyze(
                        interview_explainer_prompt(ctx),
                        task="interview",
                    )
                    self._update_step(result, "interview", "done", _ms(t))
                except Exception as e:
                    self._record_stage_error(result, "interview", str(e))
                    logger.error(f"Interview failed: {e}")

            async def _views():
                t = time.monotonic()
                self._update_step(result, "views", "running")
                try:
                    ctx = (
                        f"Overview: {truncate(json.dumps(result.repo_overview), 800)}\n"
                        f"Tech: {truncate(json.dumps(result.tech_stack), 600)}\n"
                        f"Modules: {truncate(json.dumps(result.modules), 800)}\n"
                        f"Flow: {truncate(json.dumps(result.system_flow), 800)}\n"
                        f"Health: overall={result.health_dashboard.get('overall_score', 'N/A') if result.health_dashboard else 'N/A'}"
                    )
                    result.abstraction_views = await self._llm_analyze(
                        abstraction_views_prompt(ctx),
                        task="views",
                    )
                    self._update_step(result, "views", "done", _ms(t))
                except Exception as e:
                    self._record_stage_error(result, "views", str(e))
                    logger.error(f"Abstraction views failed: {e}")

            await asyncio.gather(
                asyncio.create_task(_interview()),
                asyncio.create_task(_views()),
            )

            # Recommendations
            t0 = time.monotonic()
            self._update_step(result, "recommendations", "running")
            try:
                rec_context = (
                    f"Overview: {truncate(json.dumps(result.repo_overview), 800)}\n"
                    f"Tech: {truncate(json.dumps(result.tech_stack), 600)}\n"
                    f"Modules: {truncate(json.dumps(result.modules), 800)}\n"
                    f"Health: {truncate(json.dumps(result.health_dashboard), 800)}\n"
                    f"Security: {truncate(json.dumps(result.security_analysis), 600)}\n"
                    f"Production: {truncate(json.dumps(result.production_readiness), 600)}"
                )
                rec_result = await self._llm_analyze(
                    recommendation_prompt(rec_context),
                    task="recommendations", code_context=rec_context,
                )
                if isinstance(rec_result, dict) and "recommendations" in rec_result:
                    result.recommendations = rec_result["recommendations"]
                elif isinstance(rec_result, list):
                    result.recommendations = rec_result
                else:
                    result.recommendations = [rec_result]
                self._update_step(result, "recommendations", "done", _ms(t0))
            except Exception as e:
                self._record_stage_error(result, "recommendations", str(e))
                logger.error(f"Recommendations failed: {e}")

            # --- LLM-Enhanced Advanced Analysis (parallel) ---
            async def _threat_model():
                t = time.monotonic()
                self._update_step(result, "threat_model", "running")
                try:
                    sec_findings = json.dumps(result.security_threats, indent=2, default=str) if result.security_threats else "{}"
                    result.security_threats = result.security_threats or {}
                    llm_threats = await self._llm_analyze(
                        threat_model_prompt(truncate(overview_context, 3000), truncate(sec_findings, 2000)),
                        task="security", code_context=overview_context,
                    )
                    # Merge static + LLM threats
                    if isinstance(result.security_threats, dict):
                        result.security_threats["llm_threat_model"] = llm_threats
                    self._update_step(result, "threat_model", "done", _ms(t))
                except Exception as e:
                    self._record_stage_error(result, "threat_model", str(e))
                    logger.error(f"Threat model failed: {e}")

            async def _auto_docs():
                t = time.monotonic()
                self._update_step(result, "auto_docs", "running")
                try:
                    doc_ctx = (
                        f"Overview: {truncate(json.dumps(result.repo_overview), 800)}\n"
                        f"Tech: {truncate(json.dumps(result.tech_stack), 600)}\n"
                        f"Modules: {truncate(json.dumps(result.modules), 800)}\n"
                        f"API: {truncate(json.dumps(result.api_contracts), 800)}\n"
                        f"Config: {truncate(config_context, 1000)}"
                    )
                    result.auto_docs = await self._llm_analyze(
                        auto_doc_prompt(doc_ctx),
                        task="views",
                    )
                    self._update_step(result, "auto_docs", "done", _ms(t))
                except Exception as e:
                    self._record_stage_error(result, "auto_docs", str(e))
                    logger.error(f"Auto docs failed: {e}")

            async def _failure_modes():
                t = time.monotonic()
                self._update_step(result, "failure_analysis", "running")
                try:
                    # Combine static predictions with LLM analysis
                    static_failures = self.failure_predictor.predict(
                        parsed_files, dep_data, call_data,
                        result.health_dashboard or {},
                    )
                    result.failure_modes = static_failures
                    fail_ctx = json.dumps(static_failures, indent=2, default=str)
                    llm_failures = await self._llm_analyze(
                        failure_analysis_prompt(truncate(overview_context, 3000), truncate(fail_ctx, 2000)),
                        task="production", code_context=overview_context,
                    )
                    result.failure_modes["llm_analysis"] = llm_failures
                    self._update_step(result, "failure_analysis", "done", _ms(t))
                except Exception as e:
                    self._record_stage_error(result, "failure_analysis", str(e))
                    logger.error(f"Failure analysis failed: {e}")

            await asyncio.gather(
                asyncio.create_task(_threat_model()),
                asyncio.create_task(_auto_docs()),
                asyncio.create_task(_failure_modes()),
            )

            # Master Synthesis
            t0 = time.monotonic()
            self._update_step(result, "synthesis", "running")
            try:
                health_scores = {}
                if result.health_dashboard:
                    health_scores = {
                        "overall": result.health_dashboard.get("overall_score"),
                        "code_quality": (result.health_dashboard.get("code_quality", {}) or {}).get("score"),
                        "production": (result.health_dashboard.get("production_readiness", {}) or {}).get("score"),
                        "security": (result.health_dashboard.get("security", {}) or {}).get("score"),
                        "scalability": (result.health_dashboard.get("scalability", {}) or {}).get("score"),
                    }
                synthesis_context = (
                    f"Overview: {truncate(json.dumps(result.repo_overview), 800)}\n"
                    f"Tech: {truncate(json.dumps(result.tech_stack), 600)}\n"
                    f"Modules: {truncate(json.dumps(result.modules), 800)}\n"
                    f"Flow: {truncate(json.dumps(result.system_flow), 800)}\n"
                    f"Health scores: {json.dumps(health_scores)}\n"
                    f"Production: {truncate(json.dumps(result.production_readiness), 600)}\n"
                    f"Security: {truncate(json.dumps(result.security_analysis), 600)}"
                )
                result.master_synthesis = await self._llm_analyze(
                    master_synthesis_prompt(synthesis_context),
                    task="synthesis", code_context=synthesis_context,
                )
                self._update_step(result, "synthesis", "done", _ms(t0))
            except Exception as e:
                self._record_stage_error(result, "synthesis", str(e))
                logger.error(f"Synthesis failed: {e}")

            result.status = AnalysisStatus.COMPLETED
            result.current_phase = "completed"
            logger.info("Analysis completed!")

            # Cache the result in memory and on disk
            self._result_cache[cache_key] = result
            try:
                cache.set("result", cache_key, result.model_dump())
                logger.info(f"Result cached to disk (TTL={settings.result_cache_ttl}s)")
            except Exception as e:
                logger.warning(f"Failed to cache result to disk: {e}")

        except ConnectionError as e:
            result.status = AnalysisStatus.FAILED
            result.current_phase = "failed"
            result.errors.append(str(e))
            logger.error(f"Connection error: {e}")
        except Exception as e:
            result.status = AnalysisStatus.FAILED
            result.current_phase = "failed"
            result.errors.append(str(e))
            logger.error(f"Analysis failed: {e}", exc_info=True)

        return result

    async def _llm_analyze(self, prompt: str, task: str = "deep", code_context: str = None) -> dict:
        """Run LLM analysis with model routing, optional CoT, and cache.

        Args:
            prompt: The analysis prompt
            task: Task name for model routing (e.g. "overview", "file_analysis")
            code_context: Raw code context for CoT fact extraction (optional)
        """
        import hashlib
        # Stable cache key (not Python hash())
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:14]
        cached = cache.get("llm", prompt_hash)
        if cached:
            return cached

        # Decide: CoT (multi-step) or single-shot
        use_cot = (
            settings.cot_enabled
            and task in self.COT_TASKS
            and code_context is not None
        )

        if use_cot:
            # Get the model for this task via router
            model = await model_router.get_model_for_task(task)
            result = await cot_pipeline.analyze(
                code_context=code_context,
                analysis_prompt=prompt,
                task=task,
                model=model,
            )
        else:
            # Single-shot with model routing
            result = await model_router.generate_json(task, prompt, system_prompt=SYSTEM_PROMPT)

        # Cache the response
        cache.set("llm", prompt_hash, result)
        return result

    async def get_impact_analysis(self, repo_url: str, target: str, target_type: str = "file") -> dict:
        """On-demand impact analysis for a specific file or function."""
        parsed_files = self._parsed_cache.get(repo_url)
        if not parsed_files:
            return {"error": "Repo not analyzed yet. Run analysis first."}

        if target_type == "file":
            graph_impact = self.impact_analyzer.analyze_file_impact(
                target, parsed_files, self._modules_cache.get(repo_url)
            )
        else:
            call_data = self._call_cache.get(repo_url, {})
            graph_impact = self.impact_analyzer.analyze_function_impact(target, call_data)

        # Enhance with LLM
        file_summary = []
        for pf in parsed_files[:30]:
            funcs = [f["name"] for f in pf["functions"]]
            file_summary.append(f"  {pf['file_path']} - functions: {funcs}")
        system_context = "\n".join(file_summary)

        llm_impact = await self._llm_analyze(
            impact_analysis_llm_prompt(
                target,
                truncate(system_context, 3000),
                json.dumps(graph_impact, indent=2),
            )
        )
        graph_impact["semantic_analysis"] = llm_impact
        return graph_impact

    async def query_codebase(self, question: str, collection_name: str, repo_url: str = "") -> dict:
        """Advanced RAG query: hybrid search (BM25 + vector) → re-rank → LLM answer."""
        # Try hybrid search first (BM25 + vector + RRF re-ranking)
        relevant = []
        search_method = "vector"

        if repo_url and repo_url in self._hybrid_search_cache:
            hybrid = self._hybrid_search_cache[repo_url]
            hybrid_results = hybrid.search(question, n_results=8)
            if hybrid_results:
                relevant = hybrid_results
                search_method = "hybrid"
                logger.info(
                    f"Hybrid search: {len(relevant)} results "
                    f"(sources: {set(s for r in relevant for s in r.get('sources', []))})"
                )

        # Fallback to vector-only
        if not relevant:
            vector_results = vector_store.query(question, n_results=8, collection_name=collection_name)
            if vector_results:
                relevant = vector_results
            else:
                # Last resort: search all collections
                logger.info(f"Collection {collection_name} empty, searching all collections...")
                try:
                    for col in vector_store.client.list_collections():
                        if col.count() > 0:
                            relevant = vector_store.query(question, n_results=8, collection_name=col.name)
                            if relevant:
                                logger.info(f"Found results in fallback collection: {col.name}")
                                break
                except Exception as e:
                    logger.warning(f"Fallback collection search failed: {e}")

        if not relevant:
            return {
                "answer": "No relevant code found in the codebase for this question.",
                "relevant_files": [],
                "confidence": 0.0,
                "sources": [],
                "search_method": search_method,
            }

        # Build context from results — prioritize function/class chunks over file chunks
        relevant_sorted = sorted(
            relevant,
            key=lambda r: (
                0 if r.get("metadata", {}).get("chunk_type") == "function" else
                1 if r.get("metadata", {}).get("chunk_type") == "class" else 2
            ),
        )

        context_parts = []
        seen_files = set()
        for r in relevant_sorted:
            meta = r.get("metadata", {})
            fp = meta.get("file_path", "unknown")
            chunk_type = meta.get("chunk_type", "unknown")
            content = r.get("content", "")

            # Show chunk type and ranking info
            rank_info = ""
            if "rrf_score" in r:
                rank_info = f" [RRF: {r['rrf_score']:.4f}]"
            elif "distance" in r:
                rank_info = f" [dist: {r['distance']:.3f}]"

            context_parts.append(
                f"--- {fp} ({chunk_type}, L{meta.get('start_line', '?')}-{meta.get('end_line', '?')}){rank_info} ---\n"
                f"{content}"
            )
            seen_files.add(fp)

        context = "\n\n".join(context_parts)

        prompt = f"""You are a code analysis assistant. Answer the following question about the codebase using ONLY the provided code context.
Be specific and reference file names, function names, and line numbers when possible.

Question: {question}

Code Context (ranked by relevance):
{context}

You MUST respond with valid JSON only, no other text:
{{"answer": "your detailed answer here", "relevant_files": ["file1.py", "file2.js"], "confidence": 0.85}}"""

        # Don't use _llm_analyze (which caches) — queries should always be fresh
        system = "You are a helpful code analysis assistant. Always respond with valid JSON."
        raw = await ollama_client.generate(prompt, system_prompt=system)
        logger.info(f"RAG raw response ({search_method}): {raw[:300]}")

        # Parse JSON from the raw response
        import json as _json
        result = {}
        try:
            result = _json.loads(raw)
        except _json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    result = _json.loads(raw[start:end])
                except _json.JSONDecodeError:
                    pass

        # If JSON parsing totally failed, use the raw text
        if not result or "raw_response" in result:
            result = {
                "answer": result.get("raw_response", raw),
                "relevant_files": list(seen_files),
                "confidence": 0.5,
            }

        result["sources"] = [r.get("metadata", r) for r in relevant_sorted]
        result["search_method"] = search_method
        return result


def _ms(t0: float) -> int:
    """Convert monotonic start time to elapsed milliseconds."""
    return int((time.monotonic() - t0) * 1000)
