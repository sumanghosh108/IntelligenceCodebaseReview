"""FastAPI routes for the analysis API — job_id-based."""
import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from backend.models.schemas import RepoRequest, AnalysisResult, AnalysisStatus
from backend.analysis.engine import AnalysisEngine
from backend.llm.ollama_client import ollama_client
from backend.embeddings.vector_store import vector_store
from backend.export.zip_generator import generate_zip
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory store keyed by job_id
analysis_store: dict[str, AnalysisResult] = {}
# Reverse lookup: repo_url → list of job_ids (most recent last)
repo_jobs: dict[str, list[str]] = {}
engine = AnalysisEngine()


class QueryRequest(BaseModel):
    repo_url: str
    question: str


class AgentQueryRequest(BaseModel):
    question: str


class ImpactRequest(BaseModel):
    target: str
    target_type: str = "file"  # "file" or "function"


class AnalysisResponse(BaseModel):
    job_id: str
    status: str
    message: str
    repo_url: str


@router.get("/health")
async def health():
    ollama_ok = await ollama_client.check_health()
    models = await ollama_client.list_models() if ollama_ok else []
    return {
        "status": "healthy",
        "ollama_connected": ollama_ok,
        "available_models": models,
    }


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_repo(request: RepoRequest, background_tasks: BackgroundTasks):
    repo_url = request.repo_url.strip()

    # Check if there's already an in-progress analysis for this repo
    if repo_url in repo_jobs:
        for jid in reversed(repo_jobs[repo_url]):
            if jid in analysis_store and analysis_store[jid].status in (
                AnalysisStatus.PENDING, AnalysisStatus.CLONING,
                AnalysisStatus.PARSING, AnalysisStatus.EMBEDDING,
                AnalysisStatus.ANALYZING,
            ):
                return AnalysisResponse(
                    job_id=jid,
                    status="in_progress",
                    message="Analysis already in progress",
                    repo_url=repo_url,
                )

    # Create new job
    job_id = str(uuid.uuid4())
    result = AnalysisResult(
        job_id=job_id,
        repo_url=repo_url,
        branch=request.branch or "main",
        status=AnalysisStatus.PENDING,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    analysis_store[job_id] = result
    repo_jobs.setdefault(repo_url, []).append(job_id)

    # Run analysis in background
    background_tasks.add_task(_run_analysis, job_id, repo_url, request.branch)

    return AnalysisResponse(
        job_id=job_id,
        status="started",
        message="Analysis started. Poll /analysis/{job_id}/status for progress.",
        repo_url=repo_url,
    )


async def _run_analysis(job_id: str, repo_url: str, branch: str):
    try:
        result_ref = analysis_store[job_id]
        await engine.analyze_repo(repo_url, branch, result_ref=result_ref)
    except Exception as e:
        logger.error(f"Analysis failed for job {job_id}: {e}", exc_info=True)
        if job_id in analysis_store:
            analysis_store[job_id].status = AnalysisStatus.FAILED
            analysis_store[job_id].errors.append(str(e))


@router.get("/analysis/{job_id}/status")
async def analysis_status(job_id: str):
    result = _get_job(job_id)
    return {
        "job_id": result.job_id,
        "status": result.status,
        "current_phase": result.current_phase,
        "progress_steps": result.progress_steps,
        "quick_stats": result.quick_stats,
        "stage_errors": result.stage_errors,
        "errors": result.errors,
    }


@router.get("/analysis/{job_id}/result")
async def analysis_result(job_id: str):
    result = _get_job(job_id)
    if result.status != AnalysisStatus.COMPLETED:
        return {
            "job_id": job_id,
            "status": result.status,
            "message": "Analysis not yet complete",
        }
    return result.model_dump()


@router.get("/analysis/{job_id}/meta")
async def analysis_meta(job_id: str):
    """Metadata about the analysis job."""
    result = _get_job(job_id)
    return {
        "job_id": result.job_id,
        "repo_url": result.repo_url,
        "branch": result.branch,
        "status": result.status,
        "created_at": result.created_at,
        "current_phase": result.current_phase,
        "quick_stats": result.quick_stats,
        "stage_errors": result.stage_errors,
        "total_steps": len(result.progress_steps),
        "completed_steps": sum(1 for s in result.progress_steps if s.get("status") == "done"),
        "failed_steps": sum(1 for s in result.progress_steps if s.get("status") == "failed"),
    }


@router.get("/analysis/{job_id}/overview")
async def analysis_overview(job_id: str):
    result = _get_completed(job_id)
    return {"repo_overview": result.repo_overview}


@router.get("/analysis/{job_id}/tech-stack")
async def analysis_tech_stack(job_id: str):
    result = _get_completed(job_id)
    return {"tech_stack": result.tech_stack}


@router.get("/analysis/{job_id}/modules")
async def analysis_modules(job_id: str):
    result = _get_completed(job_id)
    return {"modules": result.modules}


@router.get("/analysis/{job_id}/files")
async def analysis_files(job_id: str):
    result = _get_completed(job_id)
    return {"file_analyses": result.file_analyses}


@router.get("/analysis/{job_id}/functions")
async def analysis_functions(job_id: str):
    result = _get_completed(job_id)
    return {"function_analyses": result.function_analyses}


@router.get("/analysis/{job_id}/dependencies")
async def analysis_dependencies(job_id: str):
    result = _get_completed(job_id)
    return {"dependencies": result.dependencies}


@router.get("/analysis/{job_id}/flow")
async def analysis_flow(job_id: str):
    result = _get_completed(job_id)
    return {
        "system_flow": result.system_flow,
        "flow_diagram": result.flow_diagram,
    }


@router.get("/analysis/{job_id}/production-readiness")
async def analysis_production(job_id: str):
    result = _get_completed(job_id)
    return {"production_readiness": result.production_readiness}


@router.get("/analysis/{job_id}/security")
async def analysis_security(job_id: str):
    result = _get_completed(job_id)
    return {"security_analysis": result.security_analysis}


@router.get("/analysis/{job_id}/cost")
async def analysis_cost(job_id: str):
    result = _get_completed(job_id)
    return {"cost_analysis": result.cost_analysis}


@router.get("/analysis/{job_id}/interview")
async def analysis_interview(job_id: str):
    result = _get_completed(job_id)
    return {"interview_explainer": result.interview_explainer}


@router.get("/analysis/{job_id}/synthesis")
async def analysis_synthesis(job_id: str):
    result = _get_completed(job_id)
    return {"master_synthesis": result.master_synthesis}


@router.get("/analysis/{job_id}/health-dashboard")
async def analysis_health_dashboard(job_id: str):
    result = _get_completed(job_id)
    return {"health_dashboard": result.health_dashboard}


@router.get("/analysis/{job_id}/call-graph")
async def analysis_call_graph(job_id: str):
    result = _get_completed(job_id)
    return {"call_graph": result.call_graph}


@router.get("/analysis/{job_id}/knowledge-graph")
async def analysis_knowledge_graph(job_id: str):
    result = _get_completed(job_id)
    return {"knowledge_graph": result.knowledge_graph}


@router.get("/analysis/{job_id}/code-quality")
async def analysis_code_quality(job_id: str):
    result = _get_completed(job_id)
    return {"code_quality": result.code_quality}


@router.get("/analysis/{job_id}/recommendations")
async def analysis_recommendations(job_id: str):
    result = _get_completed(job_id)
    return {"recommendations": result.recommendations}


@router.get("/analysis/{job_id}/abstraction-views")
async def analysis_abstraction_views(job_id: str):
    result = _get_completed(job_id)
    return {"abstraction_views": result.abstraction_views}


@router.get("/analysis/{job_id}/api-contracts")
async def analysis_api_contracts(job_id: str):
    result = _get_completed(job_id)
    return {"api_contracts": result.api_contracts}


@router.get("/analysis/{job_id}/db-schema")
async def analysis_db_schema(job_id: str):
    result = _get_completed(job_id)
    return {"db_schema": result.db_schema}


@router.get("/analysis/{job_id}/perf-bottlenecks")
async def analysis_perf_bottlenecks(job_id: str):
    result = _get_completed(job_id)
    return {"perf_bottlenecks": result.perf_bottlenecks}


@router.get("/analysis/{job_id}/complexity")
async def analysis_complexity(job_id: str):
    result = _get_completed(job_id)
    return {"complexity_score": result.complexity_score}


@router.get("/analysis/{job_id}/architecture")
async def analysis_architecture(job_id: str):
    result = _get_completed(job_id)
    return {"architecture_patterns": result.architecture_patterns}


@router.get("/analysis/{job_id}/security-threats")
async def analysis_security_threats(job_id: str):
    result = _get_completed(job_id)
    return {"security_threats": result.security_threats}


@router.get("/analysis/{job_id}/failure-modes")
async def analysis_failure_modes(job_id: str):
    result = _get_completed(job_id)
    return {"failure_modes": result.failure_modes}


@router.get("/analysis/{job_id}/timeline")
async def analysis_timeline(job_id: str):
    result = _get_completed(job_id)
    return {"timeline": result.timeline}


@router.get("/analysis/{job_id}/auto-docs")
async def analysis_auto_docs(job_id: str):
    result = _get_completed(job_id)
    return {"auto_docs": result.auto_docs}


@router.post("/analysis/{job_id}/impact")
async def analysis_impact(job_id: str, request: ImpactRequest):
    """On-demand impact analysis: what breaks if this file/function changes?"""
    result = _get_completed(job_id)

    impact = await engine.get_impact_analysis(
        result.repo_url, request.target, request.target_type
    )
    return {"impact": impact}


@router.get("/analysis/{job_id}/download")
async def download_report(job_id: str):
    """Download the full analysis as a structured ZIP report."""
    result = _get_completed(job_id)

    zip_buf = generate_zip(result)
    repo_name = result.repo_url.rstrip("/").split("/")[-1]
    filename = f"{repo_name}-analysis.zip"

    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/analyses")
async def list_analyses():
    """List all analysis jobs."""
    return {
        jid: {
            "repo_url": r.repo_url,
            "branch": r.branch,
            "status": r.status,
            "created_at": r.created_at,
            "errors": r.errors,
            "stage_errors": r.stage_errors,
        }
        for jid, r in analysis_store.items()
    }


@router.post("/query")
async def query_codebase(request: QueryRequest):
    from backend.utils.helpers import collection_name_for
    collection_name = collection_name_for(request.repo_url)
    try:
        result = await engine.query_codebase(request.question, collection_name, repo_url=request.repo_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analysis/{job_id}/agent-query")
async def agent_query(job_id: str, request: AgentQueryRequest):
    """AI Agent that autonomously explores the codebase to answer questions.

    Returns all agent steps then a final answer (non-streaming JSON).
    For SSE streaming, use /analysis/{job_id}/agent-query-stream.
    """
    import json as _json
    from backend.agent.agent_engine import agent_engine
    from backend.agent.tools import AgentTools
    from backend.utils.helpers import collection_name_for

    result = _get_completed(job_id)
    parsed_files = engine._parsed_cache.get(result.repo_url)
    if not parsed_files:
        raise HTTPException(status_code=400, detail="Codebase not in memory. Re-run analysis first.")

    col_name = collection_name_for(result.repo_url)
    tools = AgentTools(
        parsed_files=parsed_files,
        knowledge_graph=engine.knowledge_graph_builder,
        vector_store=vector_store,
        collection_name=col_name,
        analysis_result=result.model_dump(),
        hybrid_search=engine._hybrid_search_cache.get(result.repo_url),
    )

    steps = []
    final_answer = None
    async for event in agent_engine.run(request.question, tools):
        steps.append(event)
        if event["type"] == "answer":
            final_answer = event["content"]

    return {
        "question": request.question,
        "answer": final_answer or "Agent could not determine an answer.",
        "steps": steps,
        "total_steps": len(steps),
    }


@router.post("/analysis/{job_id}/agent-query-stream")
async def agent_query_stream(job_id: str, request: AgentQueryRequest):
    """SSE streaming version of agent query — sends events as they happen."""
    import json as _json
    from backend.agent.agent_engine import agent_engine
    from backend.agent.tools import AgentTools
    from backend.utils.helpers import collection_name_for

    result = _get_completed(job_id)
    parsed_files = engine._parsed_cache.get(result.repo_url)
    if not parsed_files:
        raise HTTPException(status_code=400, detail="Codebase not in memory. Re-run analysis first.")

    col_name = collection_name_for(result.repo_url)
    tools = AgentTools(
        parsed_files=parsed_files,
        knowledge_graph=engine.knowledge_graph_builder,
        vector_store=vector_store,
        collection_name=col_name,
        analysis_result=result.model_dump(),
        hybrid_search=engine._hybrid_search_cache.get(result.repo_url),
    )

    async def event_stream():
        async for event in agent_engine.run(request.question, tools):
            data = _json.dumps(event, default=str)
            yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _get_job(job_id: str) -> AnalysisResult:
    """Get job by ID or raise 404."""
    if job_id not in analysis_store:
        raise HTTPException(status_code=404, detail=f"No analysis found for job_id: {job_id}")
    return analysis_store[job_id]


def _get_completed(job_id: str) -> AnalysisResult:
    """Get completed job by ID or raise error."""
    result = _get_job(job_id)
    if result.status != AnalysisStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Analysis status: {result.status}")
    return result
