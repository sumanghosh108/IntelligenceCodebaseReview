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


class AnalysisResult(BaseModel):
    repo_url: str
    status: AnalysisStatus
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
    errors: list[str] = []
