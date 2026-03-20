"""All structured analysis prompts for the multi-pass pipeline.

Enhanced with:
- Semantic intelligence (deep insights, not surface descriptions)
- Confidence scoring on every output
- Multi-level abstraction views
- Recommendation engine
"""

SYSTEM_PROMPT = """You are a senior software architect and code analyst with deep expertise.
Rules:
- Only use the provided context.
- Do NOT assume anything outside the code.
- If information is missing, say "Not found in codebase".
- Be precise, structured, and technical.
- Avoid generic explanations — provide SPECIFIC insights tied to the actual code.
- Focus on real system behavior, patterns, anti-patterns, and architecture.
- Include confidence scores (0.0-1.0) for your assessments where requested.
Output must be structured and concise. Always respond in valid JSON."""


def repo_overview_prompt(context: str) -> str:
    return f"""Analyze the following repository context.

Context:
{context}

Tasks:
1. Summarize the repository in 3-5 lines.
2. What business problem does this solve?
3. Who are the target users?
4. What type of system is this? (web app, ML pipeline, API, etc.)
5. What are the core features?
6. Rate your confidence in this assessment.

Respond in JSON:
{{
  "summary": "",
  "problem": "",
  "users": "",
  "system_type": "",
  "core_features": [],
  "confidence": 0.0
}}"""


def tech_stack_prompt(context: str) -> str:
    return f"""Analyze the following configuration files.

Context:
{context}

Tasks:
1. List programming languages used.
2. List frameworks and libraries.
3. Detect database technologies.
4. Detect infrastructure tools (Docker, Kubernetes, etc.).
5. Identify AI/ML libraries if present.

Respond in JSON:
{{
  "languages": [],
  "frameworks": [],
  "libraries": [],
  "database": [],
  "infra_tools": [],
  "ai_ml": [],
  "confidence": 0.0
}}"""


def module_identification_prompt(context: str) -> str:
    return f"""Given the repository folder structure:

{context}

Tasks:
1. Identify logical modules.
2. Assign each folder to a module.
3. Describe the responsibility of each module.
4. Mention relationships between modules.

Respond in JSON array:
[
  {{
    "module": "",
    "folders": [],
    "responsibility": "",
    "depends_on": [],
    "confidence": 0.0
  }}
]"""


def file_analysis_prompt(file_path: str, code: str) -> str:
    return f"""Analyze the following file with SEMANTIC depth — don't just describe what it is, explain HOW it works and what patterns it uses.

File Path: {file_path}

Code:
{code}

Tasks:
1. What is the purpose of this file?
2. What role does it play in the system?
3. What are its key dependencies (imports)?
4. What would break if this file is removed?
5. What design patterns does it implement?
6. Are there any code smells or anti-patterns?

Respond in JSON:
{{
  "purpose": "",
  "role": "",
  "dependencies": [],
  "impact": "",
  "patterns": [],
  "code_smells": [],
  "confidence": 0.0
}}"""


def function_analysis_prompt(function_name: str, code: str) -> str:
    return f"""Analyze the following function with deep semantic understanding.

Function Name: {function_name}

Code:
{code}

Tasks:
1. What does this function do? Be specific about the algorithm/logic.
2. What are its inputs and outputs?
3. What logic does it implement?
4. Does it interact with external systems (DB, API, etc.)?
5. What edge cases might it miss?
6. Any performance concerns?

Respond in JSON:
{{
  "description": "",
  "inputs": [],
  "outputs": "",
  "logic": "",
  "external_interaction": "",
  "edge_cases": [],
  "performance_notes": "",
  "confidence": 0.0
}}"""


def dependency_analysis_prompt(context: str) -> str:
    return f"""Analyze the dependency relationships.

Context:
{context}

Tasks:
1. Which modules/files depend on each other?
2. Identify core modules (high dependency).
3. Identify isolated modules.
4. Detect circular dependencies if any.

Respond in JSON:
{{
  "core_modules": [],
  "dependent_relationships": [],
  "isolated_components": [],
  "circular_dependencies": [],
  "confidence": 0.0
}}"""


def system_flow_prompt(context: str) -> str:
    return f"""Analyze the execution flow of the system — trace the ACTUAL path from user request to response.

Context:
{context}

Tasks:
1. Identify the entry point of the system.
2. Describe step-by-step execution flow.
3. Show how data moves across modules.
4. Identify key processing stages.
5. Trace a typical end-to-end request.

Respond in JSON:
{{
  "entry_point": "",
  "steps": [],
  "data_flow": [],
  "processing_stages": [],
  "e2e_trace": "",
  "confidence": 0.0
}}"""


def flow_diagram_prompt(context: str) -> str:
    return f"""Generate a Mermaid flowchart for the system.

Context:
{context}

Rules:
- Use simple flowchart syntax
- Show main modules and flow
- Keep it readable
- Use flowchart TD direction

Respond with ONLY the mermaid code block, no JSON wrapping:
flowchart TD
    A[...] --> B[...]
    ..."""


def file_impact_prompt(file_path: str, code: str) -> str:
    return f"""Evaluate the importance of this file.

File Path: {file_path}

Code:
{code}

Tasks:
1. Is this file critical, important, or optional?
2. Why?
3. What parts of the system depend on it?

Respond in JSON:
{{
  "importance": "",
  "reason": "",
  "dependents": [],
  "confidence": 0.0
}}"""


def production_readiness_prompt(context: str) -> str:
    return f"""Evaluate the production readiness of this repository with specific evidence from the code.

Context:
{context}

Check:
- Logging (what framework? structured? levels?)
- Error handling (try/catch patterns? global handlers? recovery?)
- Config management (env vars? secrets? validation?)
- Docker/CI/CD (multi-stage? health checks? deployment strategy?)
- Scalability (stateless? connection pools? rate limiting?)

Respond in JSON:
{{
  "score": 0,
  "strengths": [],
  "weaknesses": [],
  "missing_components": [],
  "confidence": 0.0
}}"""


def security_analysis_prompt(context: str) -> str:
    return f"""Analyze the code for potential security issues. Be SPECIFIC — cite actual file paths and code patterns.

Context:
{context}

Check:
- Hardcoded secrets (API keys, passwords, tokens)
- SQL injection / command injection risks
- XSS vulnerabilities
- Authentication/authorization flaws
- Input validation gaps
- Insecure dependencies

Respond in JSON:
{{
  "issues": [
    {{
      "type": "",
      "severity": "critical|high|medium|low",
      "location": "",
      "description": "",
      "fix": ""
    }}
  ],
  "overall_severity": "",
  "recommendations": [],
  "confidence": 0.0
}}"""


def cost_analysis_prompt(context: str) -> str:
    return f"""Analyze the technologies used and estimate cost.

Context:
{context}

Tasks:
1. Identify paid services.
2. Estimate cost level (low/medium/high).
3. Suggest free/open-source alternatives.

Respond in JSON:
{{
  "paid_tools": [],
  "cost_level": "",
  "free_alternatives": [],
  "confidence": 0.0
}}"""


def interview_explainer_prompt(context: str) -> str:
    return f"""Explain this project as if answering in a technical interview.

Context:
{context}

Tasks:
1. High-level explanation (elevator pitch)
2. Architecture explanation (with tradeoffs)
3. Key challenges and how they were solved
4. Why this design was chosen over alternatives

Respond in JSON:
{{
  "explanation": "",
  "architecture": "",
  "challenges": [],
  "design_decisions": [],
  "confidence": 0.0
}}"""


def master_synthesis_prompt(all_previous_outputs: str) -> str:
    return f"""You are given structured analysis of a codebase.

Context:
{all_previous_outputs}

Tasks:
1. Create a complete system overview.
2. Summarize architecture.
3. Explain module interactions.
4. Provide end-to-end flow.
5. Highlight key strengths and weaknesses.

Respond in JSON:
{{
  "overview": "",
  "architecture": "",
  "modules": "",
  "flow": "",
  "strengths": [],
  "weaknesses": [],
  "confidence": 0.0
}}"""


# --- NEW ENHANCED PROMPTS ---

def recommendation_prompt(context: str) -> str:
    """Generate actionable improvement recommendations."""
    return f"""Based on the complete codebase analysis, generate specific, actionable recommendations.

Context:
{context}

For each recommendation:
- Be SPECIFIC (cite files, modules, patterns)
- Explain WHY
- Estimate effort (low/medium/high)
- Prioritize by impact

Categories:
1. Refactoring suggestions
2. Architecture improvements
3. Tech upgrades
4. Performance optimizations
5. Security hardening

Respond in JSON:
{{
  "recommendations": [
    {{
      "category": "",
      "title": "",
      "description": "",
      "affected_files": [],
      "effort": "low|medium|high",
      "impact": "low|medium|high",
      "priority": 1
    }}
  ],
  "confidence": 0.0
}}"""


def abstraction_views_prompt(context: str) -> str:
    """Generate multi-level abstraction views of the system."""
    return f"""Explain this codebase at three different levels of abstraction.

Context:
{context}

Generate three views:

1. BEGINNER VIEW: Explain as if to someone who has never coded before.
   - What does this software do?
   - Use simple analogies.

2. DEVELOPER VIEW: Explain for an experienced developer joining the team.
   - Module structure and responsibilities
   - Key data flows
   - Important patterns used
   - Where to start reading code

3. ARCHITECT VIEW: Explain for a system architect evaluating the design.
   - Design patterns and tradeoffs
   - Scalability considerations
   - Technical debt assessment
   - What would you change at scale?

Respond in JSON:
{{
  "beginner": {{
    "summary": "",
    "analogy": "",
    "key_concepts": []
  }},
  "developer": {{
    "summary": "",
    "module_guide": [],
    "key_patterns": [],
    "start_reading": [],
    "gotchas": []
  }},
  "architect": {{
    "summary": "",
    "design_patterns": [],
    "tradeoffs": [],
    "scalability": "",
    "technical_debt": [],
    "at_scale_changes": []
  }},
  "confidence": 0.0
}}"""


def impact_analysis_llm_prompt(target: str, context: str, graph_impact: str) -> str:
    """LLM-enhanced impact analysis combining graph data with semantic understanding."""
    return f"""Analyze the impact of modifying or removing this component.

Target: {target}

Deterministic Graph Analysis:
{graph_impact}

Full System Context:
{context}

Tasks:
1. What is the SEMANTIC importance of this component? (not just structural)
2. What business logic would be affected?
3. What user-facing features would break?
4. What is the safest approach to modifying this?

Respond in JSON:
{{
  "semantic_importance": "",
  "affected_business_logic": [],
  "affected_features": [],
  "safe_modification_steps": [],
  "risk_assessment": "",
  "confidence": 0.0
}}"""


def threat_model_prompt(context: str, security_findings: str) -> str:
    return f"""Perform a security threat model for this codebase.

Context:
{context}

Static analysis findings:
{security_findings}

Tasks:
1. Identify the top security threats (authentication, injection, data exposure, etc.)
2. Map attack surfaces (external APIs, user inputs, file uploads, etc.)
3. Assess each threat's severity and likelihood
4. Recommend specific mitigations

Respond in JSON:
{{
  "threats": [
    {{
      "threat": "description",
      "category": "injection|auth|exposure|crypto|config",
      "attack_surface": "where the attack enters",
      "severity": "critical|high|medium|low",
      "likelihood": "high|medium|low",
      "impact": "what happens if exploited",
      "mitigation": "specific fix"
    }}
  ],
  "overall_risk": "critical|high|medium|low",
  "attack_surfaces": [],
  "recommendations": [],
  "confidence": 0.0
}}"""


def auto_doc_prompt(context: str) -> str:
    return f"""Generate comprehensive documentation for this codebase.

Context:
{context}

Generate documentation that includes:
1. Project overview (what it does, who it's for)
2. Architecture description (components, data flow)
3. Setup/installation instructions (inferred from config files)
4. Key modules and their responsibilities
5. API endpoints (if detected)
6. Configuration options (env vars, settings)

Respond in JSON:
{{
  "title": "project name",
  "overview": "2-3 paragraph description",
  "architecture": "architecture description with component interactions",
  "setup": ["step 1", "step 2"],
  "modules": [{{"name": "", "description": "", "key_files": []}}],
  "api_endpoints": [{{"method": "GET", "path": "/api/...", "description": ""}}],
  "configuration": [{{"name": "ENV_VAR", "description": "", "default": ""}}],
  "tech_stack_summary": "",
  "confidence": 0.0
}}"""


def failure_analysis_prompt(context: str, static_findings: str) -> str:
    return f"""Analyze potential failure modes in this system.

Context:
{context}

Static analysis findings:
{static_findings}

Tasks:
1. Identify where the system is most likely to fail
2. Assess cascading failure risks
3. Evaluate error handling completeness
4. Suggest resilience improvements

Respond in JSON:
{{
  "failure_modes": [
    {{
      "mode": "description of failure scenario",
      "probability": "high|medium|low",
      "impact": "what breaks",
      "affected_components": [],
      "current_handling": "how the code currently handles this (or doesn't)",
      "recommendation": "how to prevent or handle"
    }}
  ],
  "resilience_score": 0.0,
  "critical_gaps": [],
  "confidence": 0.0
}}"""
