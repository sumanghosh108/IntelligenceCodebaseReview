"""All structured analysis prompts for the multi-pass pipeline."""

SYSTEM_PROMPT = """You are a senior software architect and code analyst.
Rules:
- Only use the provided context.
- Do NOT assume anything outside the code.
- If information is missing, say "Not found in codebase".
- Be precise, structured, and technical.
- Avoid generic explanations.
- Focus on real system behavior and architecture.
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

Respond in JSON:
{{
  "summary": "",
  "problem": "",
  "users": "",
  "system_type": "",
  "core_features": []
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
  "ai_ml": []
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
    "depends_on": []
  }}
]"""


def file_analysis_prompt(file_path: str, code: str) -> str:
    return f"""Analyze the following file.

File Path: {file_path}

Code:
{code}

Tasks:
1. What is the purpose of this file?
2. What role does it play in the system?
3. What are its key dependencies (imports)?
4. What would break if this file is removed?

Respond in JSON:
{{
  "purpose": "",
  "role": "",
  "dependencies": [],
  "impact": ""
}}"""


def function_analysis_prompt(function_name: str, code: str) -> str:
    return f"""Analyze the following function.

Function Name: {function_name}

Code:
{code}

Tasks:
1. What does this function do?
2. What are its inputs and outputs?
3. What logic does it implement?
4. Does it interact with external systems (DB, API, etc.)?

Respond in JSON:
{{
  "description": "",
  "inputs": [],
  "outputs": "",
  "logic": "",
  "external_interaction": ""
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
  "circular_dependencies": []
}}"""


def system_flow_prompt(context: str) -> str:
    return f"""Analyze the execution flow of the system.

Context:
{context}

Tasks:
1. Identify the entry point of the system.
2. Describe step-by-step execution flow.
3. Show how data moves across modules.
4. Identify key processing stages.

Respond in JSON:
{{
  "entry_point": "",
  "steps": [],
  "data_flow": [],
  "processing_stages": []
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
  "dependents": []
}}"""


def production_readiness_prompt(context: str) -> str:
    return f"""Evaluate the production readiness of this repository.

Context:
{context}

Check:
- Logging
- Error handling
- Config management
- Docker/CI/CD
- Scalability

Respond in JSON:
{{
  "score": 0,
  "strengths": [],
  "weaknesses": [],
  "missing_components": []
}}"""


def security_analysis_prompt(context: str) -> str:
    return f"""Analyze the code for potential security issues.

Context:
{context}

Check:
- Hardcoded secrets
- API keys
- Unsafe practices
- Input validation

Respond in JSON:
{{
  "issues": [],
  "severity": "",
  "recommendations": []
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
  "free_alternatives": []
}}"""


def interview_explainer_prompt(context: str) -> str:
    return f"""Explain this project as if answering in a technical interview.

Context:
{context}

Tasks:
1. High-level explanation
2. Architecture explanation
3. Key challenges
4. Why this design was chosen

Respond in JSON:
{{
  "explanation": "",
  "architecture": "",
  "challenges": [],
  "design_decisions": []
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
  "weaknesses": []
}}"""
