# Intelligence Codebase Review — Full Overview
## What It Is
A production-grade open-source codebase analysis system that takes any GitHub repo URL and produces 40+ intelligence reports using a 4-phase pipeline: deterministic parsing → graph analysis → LLM reasoning → deep analysis.

## Tech Stack
Layer	Technology
Backend	FastAPI 0.135, Uvicorn, Python 3.10
Frontend	Next.js 16, React 19, TypeScript, Tailwind CSS 4
LLM	Ollama (local, default: llama3) — fully offline
Embeddings	Sentence-Transformers (BGE-small-en-v1.5)
Vector DB	ChromaDB (persistent, cosine similarity)
Graphs	NetworkX (dependency, call, knowledge graphs)
Code Parsing	Tree-Sitter + Python AST
Git	GitPython
DevOps	Docker Compose (3 services: backend, frontend, ollama)
Architecture (4-Phase Pipeline)
Phase	Time	What Happens
Phase 1	~5s	Clone repo → parse files → quick stats
Phase 2	~15s	Health scoring, dependency/call/knowledge graphs, 7 deterministic analyzers in parallel
Phase 3	~30s	LLM: overview, tech stack, modules (hybrid model routing + Chain-of-Thought)
Phase 4	~2-5m	Deep file/function analysis, security, production readiness, threat modeling, auto-docs, synthesis
Backend Structure (37 files)
Module	Purpose
agent/	ReAct-style autonomous agent (THINK→ACT→OBSERVE loop, 9 tools)
analysis/	Multi-pass analysis engine, advanced analyzers, prompts, timeline
api/	30+ FastAPI endpoints
core/	Repo cloning, file management
embeddings/	Vector store + hybrid search (BM25 + vector + RRF re-ranking)
graphs/	Dependency, call, knowledge graphs
llm/	Ollama client, model router (fast/code/deep), Chain-of-Thought
parsers/	Tree-Sitter + AST (15+ languages)
scoring/	Health scorer, code quality analyzer
Frontend Structure (8 files)
Component	Purpose
page.tsx	Main UI — repo input, progress polling, dashboard
ResultDashboard.tsx	17-tab analysis dashboard
QueryPanel.tsx	Agent + RAG query interface with SSE streaming
StatusBanner.tsx	Live progress tracker
lib/api.ts	API client with SSE support
Analysis Outputs (40+ Reports)
Core: Overview, tech stack, modules, file/function analysis, dependencies
Graphs: Call graph, dependency graph, knowledge graph, flow diagram
Quality: Health dashboard (4 scores), code quality (rule-based + AI), complexity scoring
Security: Vulnerability scan, threat modeling, security smells (15 bandit-style patterns)
Production: Production readiness, API contracts, DB schema, performance bottlenecks
Intelligence: Architecture patterns, failure mode prediction, timeline (git history), auto-docs
Business: Cost analysis, interview explainer, recommendations, master synthesis, abstraction views

## Key Features
Fully offline — runs with local Ollama, no cloud APIs
Progressive UI — real-time phase-by-phase progress, not just a spinner
Hybrid model routing — fast model for quick tasks, deep model for reasoning
Autonomous agent — ReAct loop with 9 tools for interactive Q&A
Hybrid search — BM25 keyword + vector semantic + RRF re-ranking
Smart caching — embedding hash cache, result TTL (1hr), LLM response cache
Parallel processing — 8 parse workers, 2 LLM concurrency, 7 deterministic analyzers in parallel
15+ languages — Python, JS, TS, Go, Rust, Java, C++, C, Ruby, PHP, C#, Swift, Kotlin
Workflow

*** User submits GitHub URL ***
  → Backend clones & parses (Phase 1)
  → Deterministic scoring & graphs (Phase 2)
  → LLM analysis with model routing (Phase 3-4)
  → Frontend polls status every 1.5s, shows progress
  → Dashboard with 17+ tabs appears
  → User queries via Agent (ReAct) or RAG (hybrid search)
  → Download ZIP report