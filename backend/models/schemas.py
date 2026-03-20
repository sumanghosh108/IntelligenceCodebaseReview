"""Pydantic models for the analysis pipeline."""
from pydantic import BaseModel
from typing import Optional
from enum import Enum


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    PARSING = "parsing"
    EMBEDDING = "embedding"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisPhase(str, Enum):
    """Granular phases for progressive status tracking."""
    PENDING = "pending"
    CLONING = "cloning"
    PARSING = "parsing"
    EMBEDDING = "embedding"
    # Deterministic (fast)
    HEALTH_SCORING = "health_scoring"
    DEPENDENCY_GRAPH = "dependency_graph"
    CALL_GRAPH = "call_graph"
    # LLM passes
    OVERVIEW = "overview"
    TECH_STACK = "tech_stack"
    MODULES = "modules"
    FILE_ANALYSIS = "file_analysis"
    FUNCTION_ANALYSIS = "function_analysis"
    DEPENDENCIES_LLM = "dependencies_llm"
    SYSTEM_FLOW = "system_flow"
    FLOW_DIAGRAM = "flow_diagram"
    PRODUCTION = "production"
    SECURITY = "security"
    COST = "cost"
    INTERVIEW = "interview"
    ABSTRACTION_VIEWS = "abstraction_views"
    RECOMMENDATIONS = "recommendations"
    SYNTHESIS = "synthesis"
    COMPLETED = "completed"
    FAILED = "failed"


class RepoRequest(BaseModel):
    repo_url: str
    branch: Optional[str] = "main"


class FileInfo(BaseModel):
    path: str
    language: str
    size_bytes: int
    line_count: int


class FunctionInfo(BaseModel):
    name: str
    file_path: str
    start_line: int
    end_line: int
    parameters: list[str]
    body: str
    language: str


class ModuleInfo(BaseModel):
    module: str
    folders: list[str]
    responsibility: str
    depends_on: list[str]


class CodeChunk(BaseModel):
    chunk_id: str
    file_path: str
    chunk_type: str  # "file", "function", "class"
    content: str
    language: str
    start_line: int
    end_line: int
    metadata: dict = {}


class DependencyEdge(BaseModel):
    source: str
    target: str
    dep_type: str  # "import", "call", "inherit"


class HealthScore(BaseModel):
    name: str
    score: float
    max_score: float = 10.0
    details: list[str] = []
    issues: list[str] = []


class CodeHealthDashboard(BaseModel):
    overall_score: float = 0.0
    code_quality: Optional[dict] = None
    production_readiness: Optional[dict] = None
    security: Optional[dict] = None
    scalability: Optional[dict] = None
    recommendations: list[dict] = []
    time_to_understand: Optional[str] = None


class ImpactAnalysisResult(BaseModel):
    target: str
    target_type: str
    importance: str
    direct_dependents: list[str] = []
    indirect_dependents: list[str] = []
    affected_modules: list[str] = []
    risk_level: str = "low"
    breaking_changes: list[str] = []
    suggestions: list[str] = []


class ProgressStep(BaseModel):
    """A single step in the progressive analysis."""
    phase: str
    label: str
    status: str = "pending"  # "pending", "running", "done", "skipped"
    duration_ms: Optional[int] = None


class AnalysisResult(BaseModel):
    job_id: str = ""
    repo_url: str
    branch: str = "main"
    status: AnalysisStatus
    # Progressive tracking
    current_phase: str = "pending"
    progress_steps: list[dict] = []
    stage_errors: list[dict] = []  # [{phase, error, timestamp}]
    # Quick stats (available after parsing)
    quick_stats: Optional[dict] = None
    # Analysis results
    repo_overview: Optional[dict] = None
    tech_stack: Optional[dict] = None
    modules: Optional[list[dict]] = None
    file_analyses: Optional[list[dict]] = None
    function_analyses: Optional[list[dict]] = None
    dependencies: Optional[dict] = None
    system_flow: Optional[dict] = None
    flow_diagram: Optional[str] = None
    production_readiness: Optional[dict] = None
    security_analysis: Optional[dict] = None
    cost_analysis: Optional[dict] = None
    interview_explainer: Optional[dict] = None
    master_synthesis: Optional[dict] = None
    health_dashboard: Optional[dict] = None
    call_graph: Optional[dict] = None
    knowledge_graph: Optional[dict] = None
    recommendations: Optional[list[dict]] = None
    abstraction_views: Optional[dict] = None
    code_quality: Optional[dict] = None
    # Advanced analysis
    api_contracts: Optional[dict] = None
    db_schema: Optional[dict] = None
    perf_bottlenecks: Optional[dict] = None
    complexity_score: Optional[dict] = None
    architecture_patterns: Optional[dict] = None
    security_threats: Optional[dict] = None
    failure_modes: Optional[dict] = None
    timeline: Optional[dict] = None
    auto_docs: Optional[dict] = None
    errors: list[str] = []
    created_at: Optional[str] = None
