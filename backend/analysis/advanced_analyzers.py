"""Advanced deterministic analyzers — no LLM required.

Covers:
1. Change Impact Simulation (enhanced)
2. API Contract Detection
3. Database Schema Intelligence
4. Performance Bottleneck Detection
5. Codebase Complexity Score
6. Architecture Pattern Detection
7. Security Smell Detection (bandit-style)
8. Failure Mode Prediction

All analyzers work on parsed_files + config_files — pure static analysis.
"""
import re
import math
import logging
from pathlib import Path
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


# =============================================================================
# 1. CHANGE IMPACT SIMULATOR
# =============================================================================

class ChangeImpactSimulator:
    """Simulates the blast radius of changing any file or function."""

    def simulate(self, target: str, target_type: str,
                 parsed_files: list[dict], dep_data: dict, call_data: dict,
                 modules: list[dict] = None) -> dict:
        """Full impact simulation for a file or function change."""

        if target_type == "function":
            return self._simulate_function(target, parsed_files, call_data, modules)
        return self._simulate_file(target, parsed_files, dep_data, call_data, modules)

    def _simulate_file(self, file_path: str, parsed_files: list[dict],
                       dep_data: dict, call_data: dict, modules: list[dict]) -> dict:
        """Simulate impact of changing a file."""
        import networkx as nx

        # Build file dep graph
        G = nx.DiGraph()
        for edge in dep_data.get("edges", []):
            G.add_edge(edge["source"], edge["target"])

        if not G.has_node(file_path):
            return {"target": file_path, "risk_level": "unknown", "affected_files": [],
                    "reason": "File not found in dependency graph"}

        # Direct importers
        direct = list(G.predecessors(file_path))

        # Transitive dependents
        indirect = set()
        for d in direct:
            try:
                indirect.update(nx.ancestors(G, d))
            except Exception:
                pass
        indirect.discard(file_path)
        indirect -= set(direct)

        # Find affected functions via call graph
        affected_functions = []
        pf = next((p for p in parsed_files if p["file_path"] == file_path), None)
        if pf:
            exported = [f["name"] for f in pf["functions"]]
            for edge in call_data.get("edges", []):
                callee_parts = edge["target"].split("::")
                if len(callee_parts) == 2 and callee_parts[0] == file_path:
                    caller = edge["source"]
                    affected_functions.append({
                        "caller": caller,
                        "calls": callee_parts[1],
                    })

        # Affected modules
        affected_modules = set()
        all_affected = set(direct) | indirect
        if modules:
            for mod in modules:
                for folder in mod.get("folders", []):
                    for af in all_affected:
                        if af.startswith(folder):
                            affected_modules.add(mod.get("module", folder))

        # Risk assessment
        total_affected = len(direct) + len(indirect)
        if total_affected > 10:
            risk = "critical"
        elif total_affected > 5:
            risk = "high"
        elif total_affected > 2:
            risk = "medium"
        else:
            risk = "low"

        # Breaking change analysis
        breaking_changes = []
        if pf:
            for func in pf["functions"]:
                callers = sum(1 for e in call_data.get("edges", [])
                              if e["target"].endswith(f"::{func['name']}"))
                if callers > 0:
                    breaking_changes.append({
                        "function": func["name"],
                        "callers": callers,
                        "risk": "high" if callers > 3 else "medium",
                    })

        # Cascading failure paths
        cascade_paths = []
        if direct:
            for d in direct[:5]:
                path_deps = list(G.predecessors(d)) if G.has_node(d) else []
                if path_deps:
                    cascade_paths.append({
                        "path": f"{file_path} → {d} → {', '.join(path_deps[:3])}",
                        "depth": 2,
                        "files_at_risk": len(path_deps),
                    })

        reason = self._generate_reason(file_path, pf, total_affected, breaking_changes)

        return {
            "target": file_path,
            "target_type": "file",
            "risk_level": risk,
            "affected_files": direct + list(indirect)[:20],
            "direct_dependents": len(direct),
            "indirect_dependents": len(indirect),
            "affected_functions": affected_functions[:15],
            "affected_modules": list(affected_modules),
            "breaking_changes": breaking_changes,
            "cascade_paths": cascade_paths,
            "reason": reason,
            "suggestions": self._suggestions(risk, total_affected, breaking_changes),
        }

    def _simulate_function(self, func_name: str, parsed_files: list[dict],
                           call_data: dict, modules: list[dict]) -> dict:
        """Simulate impact of changing a function."""
        # Find callers
        callers = []
        callees = []
        for edge in call_data.get("edges", []):
            if edge["target"].endswith(f"::{func_name}"):
                callers.append(edge["source"])
            if edge["source"].endswith(f"::{func_name}"):
                callees.append(edge["target"])

        # Transitive callers (who calls the callers?)
        indirect_callers = []
        for caller in callers:
            for edge in call_data.get("edges", []):
                if edge["target"] == caller and edge["source"] not in callers:
                    indirect_callers.append(edge["source"])

        total = len(callers) + len(indirect_callers)
        risk = "critical" if total > 8 else "high" if total > 4 else "medium" if total > 1 else "low"

        return {
            "target": func_name,
            "target_type": "function",
            "risk_level": risk,
            "affected_files": list(set(c.split("::")[0] for c in callers if "::" in c)),
            "direct_callers": callers,
            "indirect_callers": indirect_callers[:10],
            "calls_to": callees,
            "reason": f"Function `{func_name}` has {len(callers)} direct callers and {len(indirect_callers)} indirect callers",
            "suggestions": self._suggestions(risk, total, []),
        }

    def _generate_reason(self, file_path: str, pf: dict, total_affected: int,
                         breaking: list[dict]) -> str:
        name = Path(file_path).name
        if total_affected == 0:
            return f"`{name}` is isolated — no detected dependents"
        parts = [f"`{name}` affects {total_affected} files"]
        if breaking:
            critical = [b for b in breaking if b["risk"] == "high"]
            if critical:
                parts.append(f"with {len(critical)} high-risk function changes")
        if pf:
            func_count = len(pf["functions"])
            if func_count > 10:
                parts.append(f"({func_count} functions exposed)")
        return ", ".join(parts)

    def _suggestions(self, risk: str, total: int, breaking: list[dict]) -> list[str]:
        suggestions = []
        if risk in ("critical", "high"):
            suggestions.append("Write comprehensive tests before modifying")
            suggestions.append("Consider phased rollout with feature flags")
            suggestions.append("Review all dependent files for compatibility")
        if total > 5:
            suggestions.append("Consider introducing an interface/abstraction to reduce coupling")
        if breaking and any(b["callers"] > 5 for b in breaking):
            suggestions.append("Deprecate old API before removing — add a compatibility shim")
        if risk == "low":
            suggestions.append("Safe to modify — minimal blast radius")
        return suggestions


# =============================================================================
# 2. API CONTRACT DETECTOR
# =============================================================================

class APIContractDetector:
    """Detects REST/GraphQL API endpoints, request/response schemas."""

    def detect(self, parsed_files: list[dict], config_files: dict) -> dict:
        endpoints = []
        framework = "unknown"

        for pf in parsed_files:
            source = pf.get("source_preview", "")
            fp = pf["file_path"]

            # FastAPI
            fastapi_routes = re.findall(
                r'@\w+\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
                source, re.IGNORECASE,
            )
            if fastapi_routes:
                framework = "FastAPI"
                for method, path in fastapi_routes:
                    endpoint = self._parse_fastapi_endpoint(method, path, source, fp, pf)
                    endpoints.append(endpoint)

            # Express.js
            express_routes = re.findall(
                r'(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
                source, re.IGNORECASE,
            )
            if express_routes:
                framework = "Express"
                for method, path in express_routes:
                    endpoints.append({
                        "endpoint": path,
                        "method": method.upper(),
                        "file": fp,
                        "input": [],
                        "output": "unknown",
                        "auth_required": "auth" in source.lower() and ("middleware" in source.lower() or "protect" in source.lower()),
                    })

            # Flask
            flask_routes = re.findall(
                r'@\w+\.route\s*\(\s*["\']([^"\']+)["\'](?:.*?methods\s*=\s*\[([^\]]+)\])?',
                source, re.DOTALL,
            )
            if flask_routes:
                framework = "Flask"
                for path, methods_str in flask_routes:
                    methods = re.findall(r'["\'](\w+)["\']', methods_str) if methods_str else ["GET"]
                    for method in methods:
                        endpoints.append({
                            "endpoint": path,
                            "method": method.upper(),
                            "file": fp,
                            "input": [],
                            "output": "unknown",
                            "auth_required": False,
                        })

            # Spring Boot (Java)
            spring_routes = re.findall(
                r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']',
                source,
            )
            if spring_routes:
                framework = "Spring Boot"
                for mapping, path in spring_routes:
                    method_map = {"GetMapping": "GET", "PostMapping": "POST",
                                  "PutMapping": "PUT", "DeleteMapping": "DELETE",
                                  "RequestMapping": "GET"}
                    endpoints.append({
                        "endpoint": path,
                        "method": method_map.get(mapping, "GET"),
                        "file": fp,
                        "input": [],
                        "output": "unknown",
                        "auth_required": False,
                    })

        # Deduplicate
        seen = set()
        unique = []
        for ep in endpoints:
            key = f"{ep['method']}:{ep['endpoint']}"
            if key not in seen:
                seen.add(key)
                unique.append(ep)

        return {
            "framework": framework,
            "total_endpoints": len(unique),
            "endpoints": unique,
            "by_method": dict(Counter(ep["method"] for ep in unique)),
            "auth_endpoints": sum(1 for ep in unique if ep.get("auth_required")),
        }

    def _parse_fastapi_endpoint(self, method: str, path: str, source: str,
                                file_path: str, pf: dict) -> dict:
        """Extract input/output info from FastAPI endpoint."""
        # Find the function after the decorator
        pattern = rf'@\w+\.{method}\s*\(\s*["\'{re.escape(path)}["\'].*?\)\s*\n\s*async\s+def\s+\w+\s*\(([^)]*)\)'
        match = re.search(pattern, source, re.DOTALL)

        params = []
        response_model = "unknown"
        if match:
            params_str = match.group(1)
            # Extract parameter names and types
            for param in params_str.split(","):
                param = param.strip()
                if param and param not in ("self",):
                    name = param.split(":")[0].strip()
                    ptype = param.split(":")[1].strip() if ":" in param else "unknown"
                    if name not in ("request", "background_tasks", "response"):
                        params.append(f"{name}: {ptype}")

        # Check for response_model
        resp_match = re.search(
            rf'@\w+\.{method}\s*\([^)]*response_model\s*=\s*(\w+)',
            source,
        )
        if resp_match:
            response_model = resp_match.group(1)

        # Check auth
        auth_required = any(kw in source for kw in ["Depends(", "Security(", "oauth2", "jwt", "token"])

        return {
            "endpoint": path,
            "method": method.upper(),
            "file": file_path,
            "input": params,
            "output": response_model,
            "auth_required": auth_required,
        }


# =============================================================================
# 3. DATABASE SCHEMA INTELLIGENCE
# =============================================================================

class DatabaseSchemaDetector:
    """Detects database models, tables, and relationships from ORM code."""

    def detect(self, parsed_files: list[dict], config_files: dict) -> dict:
        models = []
        orm = "unknown"

        for pf in parsed_files:
            source = pf.get("source_preview", "")
            fp = pf["file_path"]

            # SQLAlchemy
            sa_models = re.findall(
                r'class\s+(\w+)\s*\(.*?(?:Base|Model|db\.Model).*?\):', source
            )
            if sa_models:
                orm = "SQLAlchemy"
                for name in sa_models:
                    model = self._parse_sqlalchemy_model(name, source, fp)
                    if model:
                        models.append(model)

            # Django ORM
            django_models = re.findall(
                r'class\s+(\w+)\s*\(.*?models\.Model.*?\):', source
            )
            if django_models:
                orm = "Django ORM"
                for name in django_models:
                    model = self._parse_django_model(name, source, fp)
                    if model:
                        models.append(model)

            # Prisma (TypeScript)
            prisma_models = re.findall(r'model\s+(\w+)\s*\{([^}]+)\}', source)
            if prisma_models:
                orm = "Prisma"
                for name, body in prisma_models:
                    fields = re.findall(r'(\w+)\s+(\w+)', body)
                    models.append({
                        "name": name,
                        "file": fp,
                        "fields": [{"name": f[0], "type": f[1]} for f in fields],
                        "relationships": [],
                    })

            # Mongoose (JavaScript)
            mongoose_schemas = re.findall(
                r'new\s+(?:mongoose\.)?Schema\s*\(\s*\{([^}]+)\}', source
            )
            if mongoose_schemas:
                orm = "Mongoose"

            # TypeORM
            typeorm_entities = re.findall(r'@Entity\(\)\s*class\s+(\w+)', source)
            if typeorm_entities:
                orm = "TypeORM"

        # Detect relationships between models
        relationships = self._detect_relationships(models)

        return {
            "orm": orm,
            "total_models": len(models),
            "models": models,
            "relationships": relationships,
            "tables": [m["name"] for m in models],
        }

    def _parse_sqlalchemy_model(self, name: str, source: str, fp: str) -> dict:
        # Find the class body
        pattern = rf'class\s+{name}\s*\([^)]*\):\s*\n((?:\s+.+\n)*)'
        match = re.search(pattern, source)
        if not match:
            return {"name": name, "file": fp, "fields": [], "relationships": []}

        body = match.group(1)
        fields = []
        rels = []

        # Columns
        for col_match in re.finditer(r'(\w+)\s*=\s*(?:Column|mapped_column)\s*\((\w+)', body):
            fields.append({"name": col_match.group(1), "type": col_match.group(2)})

        # Relationships
        for rel_match in re.finditer(r'(\w+)\s*=\s*relationship\s*\(\s*["\'](\w+)["\']', body):
            rels.append({"field": rel_match.group(1), "target": rel_match.group(2)})

        # ForeignKeys
        for fk_match in re.finditer(r'ForeignKey\s*\(\s*["\']([^"\']+)["\']', body):
            rels.append({"type": "foreign_key", "target": fk_match.group(1)})

        # Table name
        table_match = re.search(r'__tablename__\s*=\s*["\'](\w+)["\']', body)
        table_name = table_match.group(1) if table_match else name.lower() + "s"

        return {"name": name, "table": table_name, "file": fp, "fields": fields, "relationships": rels}

    def _parse_django_model(self, name: str, source: str, fp: str) -> dict:
        pattern = rf'class\s+{name}\s*\([^)]*\):\s*\n((?:\s+.+\n)*)'
        match = re.search(pattern, source)
        if not match:
            return {"name": name, "file": fp, "fields": [], "relationships": []}

        body = match.group(1)
        fields = []
        rels = []

        for field_match in re.finditer(r'(\w+)\s*=\s*models\.(\w+)', body):
            fname = field_match.group(1)
            ftype = field_match.group(2)
            fields.append({"name": fname, "type": ftype})
            if ftype in ("ForeignKey", "OneToOneField", "ManyToManyField"):
                target_match = re.search(rf'{fname}\s*=\s*models\.{ftype}\s*\(\s*["\']?(\w+)', body)
                if target_match:
                    rels.append({"field": fname, "type": ftype, "target": target_match.group(1)})

        return {"name": name, "file": fp, "fields": fields, "relationships": rels}

    def _detect_relationships(self, models: list[dict]) -> list[str]:
        rels = []
        model_names = {m["name"] for m in models}
        for m in models:
            for r in m.get("relationships", []):
                target = r.get("target", "")
                if target in model_names or "." in target:
                    rels.append(f"{m['name']} → {target} ({r.get('type', r.get('field', 'relation'))})")
        return rels


# =============================================================================
# 4. PERFORMANCE BOTTLENECK DETECTOR
# =============================================================================

class PerformanceDetector:
    """Detects performance anti-patterns using static analysis."""

    def detect(self, parsed_files: list[dict]) -> dict:
        issues = []

        for pf in parsed_files:
            source = pf.get("source_preview", "")
            fp = pf["file_path"]

            # N+1 query patterns
            for func in pf["functions"]:
                body = func["body"]
                # Loop with DB query inside
                if re.search(r'for\s+\w+\s+in\s+.*?:\s*\n(?:.*\n)*?.*(?:\.query|\.filter|\.find|\.get|\.fetch|execute)', body, re.MULTILINE):
                    issues.append({
                        "issue": f"Potential N+1 query in `{func['name']}`",
                        "type": "n_plus_one",
                        "impact": "O(N) database calls instead of O(1) — slow response time",
                        "fix": "Use JOIN, batch query, or eager loading (e.g., selectinload, prefetch_related)",
                        "severity": "high",
                        "file": fp,
                        "line": func["start_line"],
                    })

                # Nested loops with high complexity
                nested_for = len(re.findall(r'\bfor\b', body))
                nested_while = len(re.findall(r'\bwhile\b', body))
                total_loops = nested_for + nested_while
                if total_loops >= 3:
                    issues.append({
                        "issue": f"Triple-nested loops in `{func['name']}` ({total_loops} loops)",
                        "type": "heavy_loop",
                        "impact": f"O(n^{total_loops}) complexity — performance degrades rapidly with data size",
                        "fix": "Refactor using hash maps, sorting, or batch processing",
                        "severity": "high" if total_loops > 3 else "medium",
                        "file": fp,
                        "line": func["start_line"],
                    })

                # Synchronous I/O in async context
                if "async def" in body:
                    sync_io = re.findall(r'\b(open|requests\.get|requests\.post|urllib|time\.sleep)\b', body)
                    if sync_io:
                        issues.append({
                            "issue": f"Blocking I/O in async function `{func['name']}`: {sync_io[0]}",
                            "type": "blocking_io",
                            "impact": "Blocks the event loop, prevents concurrent request handling",
                            "fix": f"Use async alternatives (aiofiles, httpx, asyncio.sleep)",
                            "severity": "high",
                            "file": fp,
                            "line": func["start_line"],
                        })

                # String concatenation in loops
                if re.search(r'for\s+\w+\s+in\s+.*?:\s*\n(?:.*\n)*?.*\+\s*=\s*.*(?:str|["\'])', body, re.MULTILINE):
                    issues.append({
                        "issue": f"String concatenation in loop in `{func['name']}`",
                        "type": "string_concat",
                        "impact": "O(n^2) memory — creates new string each iteration",
                        "fix": "Use list + ''.join() or io.StringIO",
                        "severity": "medium",
                        "file": fp,
                        "line": func["start_line"],
                    })

            # Large file reads without streaming
            if re.search(r'\.read\(\s*\)', source) and not re.search(r'chunk|stream|iter', source, re.IGNORECASE):
                issues.append({
                    "issue": f"Full file read without streaming in `{fp}`",
                    "type": "memory_hog",
                    "impact": "Loads entire file into memory — OOM risk for large files",
                    "fix": "Read in chunks or use streaming (e.g., iter_content, readline)",
                    "severity": "medium",
                    "file": fp,
                    "line": None,
                })

            # Missing caching for repeated expensive calls
            if re.search(r'def\s+get_\w+.*?:\s*\n(?:.*\n)*?.*(?:\.query|requests\.|fetch|api)', source, re.MULTILINE):
                if not re.search(r'cache|lru_cache|memoize|redis', source, re.IGNORECASE):
                    issues.append({
                        "issue": f"Uncached data fetching in `{fp}`",
                        "type": "no_cache",
                        "impact": "Repeated expensive calls — unnecessary latency",
                        "fix": "Add caching (lru_cache, Redis, or in-memory cache)",
                        "severity": "low",
                        "file": fp,
                        "line": None,
                    })

        # Deduplicate
        seen = set()
        unique = []
        for iss in issues:
            key = (iss["file"], iss["type"], iss.get("line"))
            if key not in seen:
                seen.add(key)
                unique.append(iss)

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        unique.sort(key=lambda x: severity_order.get(x["severity"], 3))

        return {
            "total_issues": len(unique),
            "by_type": dict(Counter(i["type"] for i in unique)),
            "by_severity": dict(Counter(i["severity"] for i in unique)),
            "issues": unique,
        }


# =============================================================================
# 5. CODEBASE COMPLEXITY SCORER
# =============================================================================

class ComplexityScorer:
    """Computes comprehensive codebase complexity metrics."""

    def score(self, parsed_files: list[dict], dep_data: dict) -> dict:
        # Cyclomatic complexity per function
        func_complexities = []
        for pf in parsed_files:
            for func in pf["functions"]:
                cc = self._cyclomatic_complexity(func["body"])
                func_complexities.append({
                    "name": func["name"],
                    "file": func["file_path"],
                    "complexity": cc,
                    "lines": func["end_line"] - func["start_line"] + 1,
                })

        # File depth (nesting in directory tree)
        max_depth = max((len(Path(pf["file_path"]).parts) for pf in parsed_files), default=0)
        avg_depth = sum(len(Path(pf["file_path"]).parts) for pf in parsed_files) / max(1, len(parsed_files))

        # Dependency density
        total_files = len(parsed_files)
        total_deps = len(dep_data.get("edges", []))
        dep_density = total_deps / max(1, total_files)

        # Average complexity
        avg_cc = sum(f["complexity"] for f in func_complexities) / max(1, len(func_complexities))
        max_cc = max((f["complexity"] for f in func_complexities), default=0)

        # Overall score (0-10, higher = more complex)
        score = 0.0
        score += min(3.0, avg_cc / 5)          # CC contribution (up to 3)
        score += min(2.0, dep_density / 3)      # Dep density contribution (up to 2)
        score += min(2.0, avg_depth / 4)        # File depth contribution (up to 2)
        score += min(1.5, total_files / 200)    # Size contribution (up to 1.5)
        score += min(1.5, max_cc / 20)          # Worst-case CC (up to 1.5)
        score = round(min(10, score), 1)

        level = "critical" if score >= 8 else "high" if score >= 6 else "moderate" if score >= 4 else "low"

        # Top complex functions
        func_complexities.sort(key=lambda x: x["complexity"], reverse=True)

        # Reasons
        reasons = []
        if avg_cc > 8:
            reasons.append(f"High average cyclomatic complexity ({avg_cc:.1f})")
        if dep_density > 4:
            reasons.append(f"Dense dependency graph ({dep_density:.1f} deps/file)")
        if max_depth > 6:
            reasons.append(f"Deep directory nesting ({max_depth} levels)")
        if max_cc > 25:
            reasons.append(f"Extremely complex function (CC={max_cc})")
        if total_files > 200:
            reasons.append(f"Large codebase ({total_files} files)")
        if not reasons:
            reasons.append("Well-structured codebase with manageable complexity")

        return {
            "complexity_score": score,
            "level": level,
            "reason": "; ".join(reasons),
            "metrics": {
                "avg_cyclomatic_complexity": round(avg_cc, 1),
                "max_cyclomatic_complexity": max_cc,
                "avg_file_depth": round(avg_depth, 1),
                "max_file_depth": max_depth,
                "dependency_density": round(dep_density, 2),
                "total_files": total_files,
                "total_functions": len(func_complexities),
                "total_dependencies": total_deps,
            },
            "hotspots": func_complexities[:10],
        }

    @staticmethod
    def _cyclomatic_complexity(body: str) -> int:
        cc = 1
        keywords = [r'\bif\b', r'\belif\b', r'\bfor\b', r'\bwhile\b',
                     r'\bexcept\b', r'\bcatch\b', r'\bcase\b',
                     r'\band\b', r'\bor\b', r'\b&&\b', r'\b\|\|\b',
                     r'\?\s*\w', r'\?\?']
        for kw in keywords:
            cc += len(re.findall(kw, body))
        return cc


# =============================================================================
# 6. ARCHITECTURE PATTERN DETECTOR
# =============================================================================

class ArchitectureDetector:
    """Detects architectural patterns from codebase structure."""

    def detect(self, parsed_files: list[dict], folder_structure: dict,
               config_files: dict) -> dict:
        patterns = []
        all_source = "\n".join(pf.get("source_preview", "") for pf in parsed_files)
        all_paths = [pf["file_path"] for pf in parsed_files]
        dirs = set(str(Path(fp).parent) for fp in all_paths)
        top_dirs = set(Path(fp).parts[0] if len(Path(fp).parts) > 1 else "root" for fp in all_paths)

        # MVC
        mvc_score = 0
        if any("model" in d.lower() for d in dirs):
            mvc_score += 0.3
        if any("view" in d.lower() or "template" in d.lower() for d in dirs):
            mvc_score += 0.3
        if any("controller" in d.lower() or "handler" in d.lower() for d in dirs):
            mvc_score += 0.3
        if any("route" in d.lower() for d in dirs):
            mvc_score += 0.1
        if mvc_score >= 0.6:
            patterns.append({"pattern": "MVC", "confidence": round(mvc_score, 2),
                             "evidence": "Separate model/view/controller directories"})

        # Layered Architecture
        layer_score = 0
        layer_dirs = {"api", "routes", "service", "services", "repository", "repositories",
                      "domain", "core", "infrastructure", "data", "presentation"}
        matched = layer_dirs & {d.lower().split("/")[-1] for d in dirs}
        if len(matched) >= 3:
            layer_score = min(1.0, len(matched) / 4)
            patterns.append({"pattern": "Layered Architecture", "confidence": round(layer_score, 2),
                             "evidence": f"Layer directories: {matched}"})

        # Microservices
        micro_score = 0
        docker_compose = config_files.get("docker-compose.yml", "") or config_files.get("docker-compose.yaml", "")
        if "services:" in docker_compose:
            service_count = docker_compose.count("image:") + docker_compose.count("build:")
            if service_count >= 2:
                micro_score = min(1.0, service_count / 5)
        if any("gateway" in fp.lower() for fp in all_paths):
            micro_score += 0.2
        if micro_score > 0.3:
            patterns.append({"pattern": "Microservices", "confidence": round(min(1.0, micro_score), 2),
                             "evidence": f"{service_count if 'service_count' in dir() else '?'} services in docker-compose"})

        # Event-Driven
        event_keywords = ["event", "listener", "handler", "subscriber", "publish", "emit",
                          "on_event", "event_bus", "message_queue", "celery", "kafka"]
        event_count = sum(1 for kw in event_keywords if kw in all_source.lower())
        if event_count >= 3:
            patterns.append({"pattern": "Event-Driven", "confidence": round(min(1.0, event_count / 6), 2),
                             "evidence": f"{event_count} event-related patterns found"})

        # Repository Pattern
        if any("repository" in fp.lower() or "repo" in fp.lower() for fp in all_paths):
            patterns.append({"pattern": "Repository Pattern", "confidence": 0.7,
                             "evidence": "Repository files/classes detected"})

        # Monolith
        if not patterns or (len(top_dirs) <= 3 and not any(p["pattern"] == "Microservices" for p in patterns)):
            patterns.append({"pattern": "Monolith", "confidence": 0.6,
                             "evidence": "Single deployment unit, all code in one repository"})

        # Sort by confidence
        patterns.sort(key=lambda x: x["confidence"], reverse=True)
        primary = patterns[0] if patterns else {"pattern": "Unknown", "confidence": 0.0}

        return {
            "primary_pattern": primary["pattern"],
            "confidence": primary["confidence"],
            "detected_patterns": patterns,
            "total_patterns": len(patterns),
        }


# =============================================================================
# 7. SECURITY SMELL DETECTOR (bandit-style)
# =============================================================================

class SecuritySmellDetector:
    """Detects security vulnerabilities using static pattern matching."""

    PATTERNS = [
        # Injection
        (r'f["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*\{', "SQL Injection",
         "String interpolation in SQL query", "critical", "Use parameterized queries"),
        (r'\.format\(.*(?:SELECT|INSERT|UPDATE|DELETE)', "SQL Injection",
         "String formatting in SQL query", "critical", "Use parameterized queries"),
        (r'eval\s*\(', "Code Injection",
         "eval() executes arbitrary code", "critical", "Use ast.literal_eval or safe parsers"),
        (r'exec\s*\(', "Code Injection",
         "exec() executes arbitrary code", "critical", "Avoid exec(), use specific functions"),
        (r'subprocess\.(?:call|run|Popen)\s*\(\s*(?:f["\']|.*\.format|.*\+)', "Command Injection",
         "User input in subprocess command", "critical", "Use subprocess with list args, never shell=True"),
        (r'os\.system\s*\(', "Command Injection",
         "os.system() is vulnerable to shell injection", "high", "Use subprocess.run() with list args"),

        # Auth/Crypto
        (r'(?:md5|sha1)\s*\(', "Weak Hashing",
         "MD5/SHA1 are cryptographically broken", "high", "Use SHA-256 or bcrypt for passwords"),
        (r'password.*=.*["\'][^"\']{3,}["\']', "Hardcoded Password",
         "Password hardcoded in source", "critical", "Use environment variables or secrets manager"),
        (r'(?:api_key|apikey|secret).*=.*["\'][^"\']{8,}["\']', "Hardcoded Secret",
         "API key or secret hardcoded", "critical", "Use environment variables"),
        (r'verify\s*=\s*False', "SSL Verification Disabled",
         "SSL certificate verification disabled", "high", "Enable SSL verification"),
        (r'debug\s*=\s*True', "Debug Mode",
         "Debug mode enabled — may expose stack traces", "medium", "Disable in production"),

        # Data exposure
        (r'CORS\s*\(\s*\w+\s*,\s*allow_origins\s*=\s*\[\s*["\*"]', "Permissive CORS",
         "CORS allows all origins", "medium", "Restrict to specific domains"),
        (r'\.(?:log|print|console\.log)\s*\(.*(?:password|token|secret|key)', "Credential Logging",
         "Sensitive data may be logged", "high", "Never log credentials or tokens"),

        # Deserialization
        (r'pickle\.load', "Unsafe Deserialization",
         "Pickle deserialization of untrusted data", "high", "Use JSON or validated schemas"),
        (r'yaml\.load\s*\((?!.*Loader)', "Unsafe YAML Loading",
         "yaml.load without safe Loader", "high", "Use yaml.safe_load()"),
    ]

    def detect(self, parsed_files: list[dict]) -> dict:
        issues = []
        for pf in parsed_files:
            source = pf.get("source_preview", "")
            fp = pf["file_path"]

            for pattern, threat, description, severity, fix in self.PATTERNS:
                matches = re.finditer(pattern, source, re.IGNORECASE)
                for match in matches:
                    line_num = source[:match.start()].count("\n") + 1
                    issues.append({
                        "threat": threat,
                        "issue": description,
                        "severity": severity,
                        "fix": fix,
                        "file": fp,
                        "line": line_num,
                        "match": match.group(0)[:80],
                    })

        # Deduplicate by file+threat
        seen = set()
        unique = []
        for iss in issues:
            key = (iss["file"], iss["threat"], iss.get("line"))
            if key not in seen:
                seen.add(key)
                unique.append(iss)

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        unique.sort(key=lambda x: severity_order.get(x["severity"], 3))

        return {
            "total_threats": len(unique),
            "by_severity": dict(Counter(i["severity"] for i in unique)),
            "by_type": dict(Counter(i["threat"] for i in unique)),
            "threats": unique,
        }


# =============================================================================
# 8. FAILURE MODE PREDICTOR
# =============================================================================

class FailureModePredictor:
    """Predicts where the system might break based on static analysis."""

    def predict(self, parsed_files: list[dict], dep_data: dict,
                call_data: dict, health_data: dict = None) -> dict:
        predictions = []

        # Single points of failure (high fan-in, no redundancy)
        hot_functions = call_data.get("hot_functions", [])
        for hf in hot_functions:
            if hf.get("callers", 0) > 5:
                predictions.append({
                    "failure_mode": f"Single Point of Failure: `{hf['name']}`",
                    "probability": "high",
                    "impact": f"{hf['callers']} callers affected if this function fails",
                    "location": f"{hf.get('file', '?')}::{hf['name']}",
                    "mitigation": "Add error handling, fallback logic, or circuit breaker",
                })

        # Unhandled error paths
        for pf in parsed_files:
            source = pf.get("source_preview", "")
            fp = pf["file_path"]

            # Async functions without try/except
            for func in pf["functions"]:
                if "async def" in func["body"] and "try:" not in func["body"]:
                    if any(kw in func["body"] for kw in ["await", "fetch", "query", "request"]):
                        predictions.append({
                            "failure_mode": f"Unhandled async error in `{func['name']}`",
                            "probability": "medium",
                            "impact": "Unhandled exception crashes the request/task",
                            "location": f"{fp}::{func['name']}",
                            "mitigation": "Wrap external calls in try/except with proper error handling",
                        })

            # Missing timeout on external calls
            if re.search(r'(?:requests|httpx|fetch|urllib)\.\w+\(', source):
                if not re.search(r'timeout\s*=', source):
                    predictions.append({
                        "failure_mode": f"Missing timeout on HTTP calls in `{fp}`",
                        "probability": "medium",
                        "impact": "Requests hang indefinitely if external service is down",
                        "location": fp,
                        "mitigation": "Add explicit timeout parameter to all HTTP calls",
                    })

            # No retry logic on external dependencies
            if re.search(r'(?:connect|\.get|\.post|\.query)\s*\(', source):
                if not re.search(r'retry|backoff|tenacity|retrying', source, re.IGNORECASE):
                    if any(kw in fp.lower() for kw in ["client", "api", "service", "connect"]):
                        predictions.append({
                            "failure_mode": f"No retry logic in `{Path(fp).name}`",
                            "probability": "medium",
                            "impact": "Transient failures cause permanent errors",
                            "location": fp,
                            "mitigation": "Add exponential backoff retry (e.g., tenacity library)",
                        })

        # Resource exhaustion risks
        for pf in parsed_files:
            source = pf.get("source_preview", "")
            if "while True" in source and "break" not in source:
                predictions.append({
                    "failure_mode": f"Potential infinite loop in `{pf['file_path']}`",
                    "probability": "low",
                    "impact": "CPU exhaustion, process hang",
                    "location": pf["file_path"],
                    "mitigation": "Add break condition or timeout",
                })

        # Deduplicate
        seen = set()
        unique = []
        for p in predictions:
            key = p["location"]
            if key not in seen:
                seen.add(key)
                unique.append(p)

        prob_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        unique.sort(key=lambda x: prob_order.get(x["probability"], 3))

        return {
            "total_predictions": len(unique),
            "by_probability": dict(Counter(p["probability"] for p in unique)),
            "predictions": unique[:25],
        }
