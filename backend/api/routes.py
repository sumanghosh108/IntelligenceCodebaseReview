"""FastAPI routes for the analysis API."""
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.models.schemas import RepoRequest, AnalysisResult, AnalysisStatus
from backend.analysis.engine import AnalysisEngine
from backend.llm.ollama_client import ollama_client
from backend.embeddings.vector_store import vector_store
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory store for analysis results
analysis_store: dict[str, AnalysisResult] = {}
engine = AnalysisEngine()


class QueryRequest(BaseModel):
    repo_url: str
    question: str


class AnalysisResponse(BaseModel):
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

    if repo_url in analysis_store and analysis_store[repo_url].status == AnalysisStatus.ANALYZING:
        return AnalysisResponse(
            status="in_progress",
            message="Analysis already in progress",
            repo_url=repo_url,
        )

    # Initialize with pending status
    analysis_store[repo_url] = AnalysisResult(
        repo_url=repo_url, status=AnalysisStatus.PENDING
    )

    # Run analysis in background
    background_tasks.add_task(_run_analysis, repo_url, request.branch)

    return AnalysisResponse(
        status="started",
        message="Analysis started. Poll /analysis/status for progress.",
        repo_url=repo_url,
    )


async def _run_analysis(repo_url: str, branch: str):
    try:
        result = await engine.analyze_repo(repo_url, branch)
        analysis_store[repo_url] = result
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        analysis_store[repo_url] = AnalysisResult(
            repo_url=repo_url,
            status=AnalysisStatus.FAILED,
            errors=[str(e)],
        )


@router.get("/analysis/status")
async def analysis_status(repo_url: str):
    if repo_url not in analysis_store:
        raise HTTPException(status_code=404, detail="No analysis found for this repo")

    result = analysis_store[repo_url]
    return {"status": result.status, "errors": result.errors}


@router.get("/analysis/result")
async def analysis_result(repo_url: str):
    if repo_url not in analysis_store:
        raise HTTPException(status_code=404, detail="No analysis found for this repo")

    result = analysis_store[repo_url]
    if result.status != AnalysisStatus.COMPLETED:
        return {"status": result.status, "message": "Analysis not yet complete"}

    return result.model_dump()


@router.get("/analysis/overview")
async def analysis_overview(repo_url: str):
    result = _get_completed(repo_url)
    return {"repo_overview": result.repo_overview}


@router.get("/analysis/tech-stack")
async def analysis_tech_stack(repo_url: str):
    result = _get_completed(repo_url)
    return {"tech_stack": result.tech_stack}


@router.get("/analysis/modules")
async def analysis_modules(repo_url: str):
    result = _get_completed(repo_url)
    return {"modules": result.modules}


@router.get("/analysis/files")
async def analysis_files(repo_url: str):
    result = _get_completed(repo_url)
    return {"file_analyses": result.file_analyses}


@router.get("/analysis/functions")
async def analysis_functions(repo_url: str):
    result = _get_completed(repo_url)
    return {"function_analyses": result.function_analyses}


@router.get("/analysis/dependencies")
async def analysis_dependencies(repo_url: str):
    result = _get_completed(repo_url)
    return {"dependencies": result.dependencies}


@router.get("/analysis/flow")
async def analysis_flow(repo_url: str):
    result = _get_completed(repo_url)
    return {
        "system_flow": result.system_flow,
        "flow_diagram": result.flow_diagram,
    }


@router.get("/analysis/production-readiness")
async def analysis_production(repo_url: str):
    result = _get_completed(repo_url)
    return {"production_readiness": result.production_readiness}


@router.get("/analysis/security")
async def analysis_security(repo_url: str):
    result = _get_completed(repo_url)
    return {"security_analysis": result.security_analysis}


@router.get("/analysis/cost")
async def analysis_cost(repo_url: str):
    result = _get_completed(repo_url)
    return {"cost_analysis": result.cost_analysis}


@router.get("/analysis/interview")
async def analysis_interview(repo_url: str):
    result = _get_completed(repo_url)
    return {"interview_explainer": result.interview_explainer}


@router.get("/analysis/synthesis")
async def analysis_synthesis(repo_url: str):
    result = _get_completed(repo_url)
    return {"master_synthesis": result.master_synthesis}


@router.post("/query")
async def query_codebase(request: QueryRequest):
    collection_name = f"repo_{hash(request.repo_url) % 100000}"
    try:
        result = await engine.query_codebase(request.question, collection_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyses")
async def list_analyses():
    return {
        url: {"status": r.status, "errors": r.errors}
        for url, r in analysis_store.items()
    }


def _get_completed(repo_url: str) -> AnalysisResult:
    if repo_url not in analysis_store:
        raise HTTPException(status_code=404, detail="No analysis found")
    result = analysis_store[repo_url]
    if result.status != AnalysisStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Analysis status: {result.status}")
    return result
