"""ZIP export generator for structured analysis reports."""
import io
import json
import zipfile
from datetime import datetime, timezone
from backend.models.schemas import AnalysisResult


def _to_json(data) -> str:
    """Serialize data to formatted JSON string."""
    return json.dumps(data, indent=2, default=str, ensure_ascii=False)


def _dict_to_md_sections(data: dict, heading_level: int = 2) -> str:
    """Convert a dict to markdown sections."""
    lines = []
    prefix = "#" * heading_level
    for key, value in data.items():
        title = key.replace("_", " ").title()
        if isinstance(value, list):
            lines.append(f"{prefix} {title}\n")
            for item in value:
                if isinstance(item, dict):
                    parts = [f"**{k}**: {v}" for k, v in item.items()]
                    lines.append(f"- {'; '.join(parts)}")
                else:
                    lines.append(f"- {item}")
            lines.append("")
        elif isinstance(value, dict):
            lines.append(f"{prefix} {title}\n")
            lines.append(_dict_to_md_sections(value, heading_level + 1))
        else:
            lines.append(f"{prefix} {title}\n")
            lines.append(f"{value}\n")
    return "\n".join(lines)


def _build_overview_md(overview: dict) -> str:
    """Build overview/summary.md."""
    lines = ["# Repository Overview\n"]
    for key in ["summary", "problem", "users", "system_type"]:
        if key in overview:
            lines.append(f"## {key.replace('_', ' ').title()}\n")
            lines.append(f"{overview[key]}\n")
    if "core_features" in overview:
        lines.append("## Core Features\n")
        for feat in overview["core_features"]:
            if isinstance(feat, dict):
                name = feat.get("name", "")
                desc = feat.get("description", "")
                lines.append(f"- **{name}**: {desc}" if desc else f"- {name}")
            else:
                lines.append(f"- {feat}")
        lines.append("")
    return "\n".join(lines)


def _build_tech_stack_md(tech: dict) -> str:
    """Build overview/tech_stack.md."""
    lines = ["# Technology Stack\n"]
    for key in ["languages", "frameworks", "libraries", "database", "infra_tools", "ai_ml"]:
        if key in tech:
            val = tech[key]
            title = key.replace("_", " ").title()
            lines.append(f"## {title}\n")
            if isinstance(val, list):
                for item in val:
                    lines.append(f"- {item}")
            else:
                lines.append(str(val))
            lines.append("")
    return "\n".join(lines)


def _build_production_readiness_md(data: dict) -> str:
    """Build reports/production_readiness.md."""
    lines = ["# Production Readiness Report\n"]
    if "score" in data:
        score = data["score"]
        lines.append(f"**Score: {score}/10**\n")
    for section in ["strengths", "weaknesses", "missing_components"]:
        if section in data:
            lines.append(f"## {section.replace('_', ' ').title()}\n")
            val = data[section]
            if isinstance(val, list):
                for item in val:
                    lines.append(f"- {item}")
            else:
                lines.append(str(val))
            lines.append("")
    return "\n".join(lines)


def _build_security_md(data: dict) -> str:
    """Build reports/security_report.md."""
    lines = ["# Security Analysis Report\n"]
    for section in ["issues", "severity", "recommendations"]:
        if section in data:
            lines.append(f"## {section.title()}\n")
            val = data[section]
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        parts = [f"**{k}**: {v}" for k, v in item.items()]
                        lines.append(f"- {'; '.join(parts)}")
                    else:
                        lines.append(f"- {item}")
            else:
                lines.append(str(val))
            lines.append("")
    return "\n".join(lines)


def _build_cost_md(data: dict) -> str:
    """Build reports/cost_analysis.md."""
    lines = ["# Cost Analysis Report\n"]
    for section in ["paid_tools", "cost_level", "free_alternatives"]:
        if section in data:
            lines.append(f"## {section.replace('_', ' ').title()}\n")
            val = data[section]
            if isinstance(val, list):
                for item in val:
                    lines.append(f"- {item}")
            else:
                lines.append(str(val))
            lines.append("")
    return "\n".join(lines)


def _build_interview_md(data: dict) -> str:
    """Build reports/interview_explainer.md."""
    lines = ["# Interview Explainer\n"]
    lines.append(
        "_How to explain this project in a technical interview._\n"
    )
    for section in ["explanation", "architecture", "challenges", "design_decisions"]:
        if section in data:
            lines.append(f"## {section.replace('_', ' ').title()}\n")
            val = data[section]
            if isinstance(val, list):
                for item in val:
                    lines.append(f"- {item}")
            else:
                lines.append(str(val))
            lines.append("")
    return "\n".join(lines)


def _build_flow_md(flow: dict, diagram: str | None) -> str:
    """Build architecture/system_flow.md."""
    lines = ["# System Execution Flow\n"]
    if "steps" in flow:
        for i, step in enumerate(flow["steps"], 1):
            if isinstance(step, dict):
                lines.append(f"{i}. **{step.get('stage', '')}**: {step.get('description', '')}")
            else:
                lines.append(f"{i}. {step}")
        lines.append("")
    else:
        lines.append(_dict_to_md_sections(flow))

    if diagram:
        lines.append("## Flow Diagram (Mermaid)\n")
        lines.append("```mermaid")
        lines.append(diagram)
        lines.append("```\n")
    return "\n".join(lines)


def _build_synthesis_md(data: dict) -> str:
    """Build the master synthesis report."""
    lines = ["# Master Synthesis Report\n"]
    for section in ["overview", "architecture", "modules", "flow", "strengths", "weaknesses"]:
        if section in data:
            lines.append(f"## {section.title()}\n")
            val = data[section]
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        parts = [f"**{k}**: {v}" for k, v in item.items()]
                        lines.append(f"- {'; '.join(parts)}")
                    else:
                        lines.append(f"- {item}")
            elif isinstance(val, dict):
                lines.append(_dict_to_md_sections(val, 3))
            else:
                lines.append(str(val))
            lines.append("")
    return "\n".join(lines)


def _build_health_md(data: dict) -> str:
    """Build health/health_dashboard.md."""
    lines = ["# Codebase Health Dashboard\n"]
    overall = data.get("overall_score", 0)
    lines.append(f"**Overall Score: {overall}/10**\n")

    stats = data.get("stats", {})
    if stats:
        lines.append("## Statistics\n")
        lines.append(f"- Total Files: {stats.get('total_files', 'N/A')}")
        lines.append(f"- Total Lines: {stats.get('total_lines', 'N/A')}")
        lines.append(f"- Total Functions: {stats.get('total_functions', 'N/A')}")
        langs = stats.get("languages", [])
        lines.append(f"- Languages: {', '.join(langs) if langs else 'N/A'}")
        lines.append("")

    ttu = data.get("time_to_understand")
    if ttu:
        lines.append(f"**Estimated Time to Understand: {ttu}**\n")

    for category in ["code_quality", "production_readiness", "security", "scalability"]:
        cat_data = data.get(category, {})
        if cat_data:
            title = category.replace("_", " ").title()
            score = cat_data.get("score", 0)
            lines.append(f"## {title} ({score}/10)\n")
            for detail in cat_data.get("details", []):
                lines.append(f"- {detail}")
            for issue in cat_data.get("issues", []):
                lines.append(f"- **Issue:** {issue}")
            lines.append("")

    return "\n".join(lines)


def _build_recommendations_md(recs: list) -> str:
    """Build reports/recommendations.md."""
    lines = ["# Improvement Recommendations\n"]
    for i, rec in enumerate(recs, 1):
        if isinstance(rec, dict):
            title = rec.get("title", f"Recommendation {i}")
            category = rec.get("category", "General")
            effort = rec.get("effort", "unknown")
            impact = rec.get("impact", "unknown")
            desc = rec.get("description", "")
            files = rec.get("affected_files", [])

            lines.append(f"## {i}. {title}\n")
            lines.append(f"**Category:** {category} | **Effort:** {effort} | **Impact:** {impact}\n")
            lines.append(f"{desc}\n")
            if files:
                lines.append("**Affected files:**")
                for f in files:
                    lines.append(f"- `{f}`")
            lines.append("")
        else:
            lines.append(f"## {i}. {rec}\n")
    return "\n".join(lines)


def _build_abstraction_views_md(views: dict) -> str:
    """Build reports/abstraction_views.md."""
    lines = ["# Multi-Level System Views\n"]

    beginner = views.get("beginner", {})
    if beginner:
        lines.append("## Beginner View\n")
        lines.append(f"{beginner.get('summary', '')}\n")
        analogy = beginner.get("analogy", "")
        if analogy:
            lines.append(f"**Analogy:** {analogy}\n")
        concepts = beginner.get("key_concepts", [])
        if concepts:
            lines.append("**Key Concepts:**")
            for c in concepts:
                lines.append(f"- {c}")
            lines.append("")

    developer = views.get("developer", {})
    if developer:
        lines.append("## Developer View\n")
        lines.append(f"{developer.get('summary', '')}\n")
        for section, title in [("module_guide", "Module Guide"), ("key_patterns", "Key Patterns"),
                                ("start_reading", "Start Reading"), ("gotchas", "Gotchas")]:
            items = developer.get(section, [])
            if items:
                lines.append(f"### {title}\n")
                for item in items:
                    if isinstance(item, dict):
                        parts = [f"**{k}**: {v}" for k, v in item.items()]
                        lines.append(f"- {'; '.join(parts)}")
                    else:
                        lines.append(f"- {item}")
                lines.append("")

    architect = views.get("architect", {})
    if architect:
        lines.append("## Architect View\n")
        lines.append(f"{architect.get('summary', '')}\n")
        for section, title in [("design_patterns", "Design Patterns"), ("tradeoffs", "Tradeoffs"),
                                ("technical_debt", "Technical Debt"), ("at_scale_changes", "At Scale Changes")]:
            items = architect.get(section, [])
            if items:
                lines.append(f"### {title}\n")
                for item in items:
                    if isinstance(item, dict):
                        parts = [f"**{k}**: {v}" for k, v in item.items()]
                        lines.append(f"- {'; '.join(parts)}")
                    else:
                        lines.append(f"- {item}")
                lines.append("")
        scalability = architect.get("scalability", "")
        if scalability:
            lines.append(f"### Scalability\n\n{scalability}\n")

    return "\n".join(lines)


def _build_readme(result: AnalysisResult) -> str:
    """Auto-generate README.md for the ZIP package."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    repo_name = result.repo_url.rstrip("/").split("/")[-1]

    sections_map = {
        "overview/summary.md": ("Repository Overview", result.repo_overview),
        "overview/tech_stack.md": ("Technology Stack", result.tech_stack),
        "overview/tech_stack.json": ("Tech Stack (JSON)", result.tech_stack),
        "architecture/system_flow.md": ("System Flow", result.system_flow),
        "architecture/module_graph.json": ("Module Dependency Graph", result.dependencies),
        "modules/": ("Module Analysis", result.modules),
        "files/file_analysis.json": ("File Analysis", result.file_analyses),
        "functions/function_analysis.json": ("Function Analysis", result.function_analyses),
        "reports/production_readiness.md": ("Production Readiness", result.production_readiness),
        "reports/security_report.md": ("Security Analysis", result.security_analysis),
        "reports/cost_analysis.md": ("Cost Analysis", result.cost_analysis),
        "reports/interview_explainer.md": ("Interview Explainer", result.interview_explainer),
        "reports/master_synthesis.md": ("Master Synthesis", result.master_synthesis),
    }

    lines = [
        f"# Codebase Analysis Report: {repo_name}",
        "",
        f"**Repository:** {result.repo_url}",
        f"**Generated:** {now}",
        f"**Tool:** Intelligence Codebase Review",
        "",
        "---",
        "",
        "## Contents",
        "",
    ]

    for path, (title, data) in sections_map.items():
        if data:
            lines.append(f"- [{title}]({path})")

    lines.extend([
        "",
        "---",
        "",
        "## Directory Structure",
        "",
        "```",
        "repo-analysis/",
        "|",
        "├── overview/           # Summary, business problem, tech stack",
        "├── architecture/       # System flow, module graph, diagrams",
        "├── modules/            # Per-module analysis",
        "├── files/              # File-level analysis",
        "├── functions/          # Function-level analysis",
        "├── reports/            # Readiness, security, cost, interview",
        "└── README.md           # This file",
        "```",
        "",
        "---",
        "",
        "*Generated by Intelligence Codebase Review — open-source codebase analysis system.*",
        "",
    ])

    return "\n".join(lines)


def generate_zip(result: AnalysisResult) -> io.BytesIO:
    """Generate a ZIP file containing the full structured analysis report.

    Returns an in-memory BytesIO buffer containing the ZIP.
    """
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        prefix = "repo-analysis"

        # --- overview/ ---
        if result.repo_overview:
            zf.writestr(
                f"{prefix}/overview/summary.md",
                _build_overview_md(result.repo_overview),
            )

        if result.tech_stack:
            zf.writestr(
                f"{prefix}/overview/tech_stack.md",
                _build_tech_stack_md(result.tech_stack),
            )
            zf.writestr(
                f"{prefix}/overview/tech_stack.json",
                _to_json(result.tech_stack),
            )

        # --- architecture/ ---
        if result.system_flow or result.flow_diagram:
            zf.writestr(
                f"{prefix}/architecture/system_flow.md",
                _build_flow_md(result.system_flow or {}, result.flow_diagram),
            )

        if result.flow_diagram:
            zf.writestr(
                f"{prefix}/architecture/flow_diagram.mmd",
                result.flow_diagram,
            )

        if result.dependencies:
            zf.writestr(
                f"{prefix}/architecture/module_graph.json",
                _to_json(result.dependencies),
            )
            # Also create a simplified markdown view
            dep_md = ["# Module Dependency Graph\n"]
            for key in ["core_modules", "dependent_relationships", "isolated_components", "circular_dependencies"]:
                if key in result.dependencies:
                    dep_md.append(f"## {key.replace('_', ' ').title()}\n")
                    val = result.dependencies[key]
                    if isinstance(val, list):
                        for item in val:
                            if isinstance(item, dict):
                                parts = [f"**{k}**: {v}" for k, v in item.items()]
                                dep_md.append(f"- {'; '.join(parts)}")
                            else:
                                dep_md.append(f"- {item}")
                    else:
                        dep_md.append(str(val))
                    dep_md.append("")
            zf.writestr(
                f"{prefix}/architecture/dependencies.md",
                "\n".join(dep_md),
            )

        # --- modules/ ---
        if result.modules:
            zf.writestr(
                f"{prefix}/modules/modules.json",
                _to_json(result.modules),
            )
            # Per-module markdown files
            for mod in result.modules:
                if isinstance(mod, dict):
                    name = mod.get("module", "unknown").replace("/", "_").replace(" ", "_").lower()
                    lines = [f"# Module: {mod.get('module', 'Unknown')}\n"]
                    lines.append(f"**Responsibility:** {mod.get('responsibility', 'N/A')}\n")
                    folders = mod.get("folders", [])
                    if folders:
                        lines.append("## Folders\n")
                        for f in folders:
                            lines.append(f"- `{f}`")
                        lines.append("")
                    deps = mod.get("depends_on", [])
                    if deps:
                        lines.append("## Dependencies\n")
                        for d in deps:
                            lines.append(f"- {d}")
                        lines.append("")
                    zf.writestr(
                        f"{prefix}/modules/{name}.md",
                        "\n".join(lines),
                    )

        # --- files/ ---
        if result.file_analyses:
            zf.writestr(
                f"{prefix}/files/file_analysis.json",
                _to_json(result.file_analyses),
            )

        # --- functions/ ---
        if result.function_analyses:
            zf.writestr(
                f"{prefix}/functions/function_analysis.json",
                _to_json(result.function_analyses),
            )

        # --- reports/ ---
        if result.production_readiness:
            zf.writestr(
                f"{prefix}/reports/production_readiness.md",
                _build_production_readiness_md(result.production_readiness),
            )

        if result.security_analysis:
            zf.writestr(
                f"{prefix}/reports/security_report.md",
                _build_security_md(result.security_analysis),
            )

        if result.cost_analysis:
            zf.writestr(
                f"{prefix}/reports/cost_analysis.md",
                _build_cost_md(result.cost_analysis),
            )

        if result.interview_explainer:
            zf.writestr(
                f"{prefix}/reports/interview_explainer.md",
                _build_interview_md(result.interview_explainer),
            )

        if result.master_synthesis:
            zf.writestr(
                f"{prefix}/reports/master_synthesis.md",
                _build_synthesis_md(result.master_synthesis),
            )

        # --- health/ (NEW) ---
        if result.health_dashboard:
            zf.writestr(
                f"{prefix}/health/health_dashboard.json",
                _to_json(result.health_dashboard),
            )
            zf.writestr(
                f"{prefix}/health/health_dashboard.md",
                _build_health_md(result.health_dashboard),
            )

        # --- call_graph/ (NEW) ---
        if result.call_graph:
            zf.writestr(
                f"{prefix}/architecture/call_graph.json",
                _to_json(result.call_graph),
            )

        # --- recommendations/ (NEW) ---
        if result.recommendations:
            zf.writestr(
                f"{prefix}/reports/recommendations.json",
                _to_json(result.recommendations),
            )
            zf.writestr(
                f"{prefix}/reports/recommendations.md",
                _build_recommendations_md(result.recommendations),
            )

        # --- abstraction views/ (NEW) ---
        if result.abstraction_views:
            zf.writestr(
                f"{prefix}/reports/abstraction_views.json",
                _to_json(result.abstraction_views),
            )
            zf.writestr(
                f"{prefix}/reports/abstraction_views.md",
                _build_abstraction_views_md(result.abstraction_views),
            )

        # --- README.md ---
        zf.writestr(
            f"{prefix}/README.md",
            _build_readme(result),
        )

    buf.seek(0)
    return buf
