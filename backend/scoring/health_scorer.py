"""Deterministic code health scoring engine.

Uses parsed data (not LLM) for scoring — Tree-sitter/AST first, LLM second.
Scores: Code Quality, Production Readiness, Security, Scalability.
"""
import re
from pathlib import Path


class HealthScorer:
    """Computes deterministic health scores from parsed codebase data."""

    def score_all(
        self,
        parsed_files: list[dict],
        config_files: dict[str, str],
        folder_structure: dict,
    ) -> dict:
        """Run all scoring passes and return aggregate health dashboard."""
        cq = self._score_code_quality(parsed_files)
        pr = self._score_production_readiness(parsed_files, config_files)
        sec = self._score_security(parsed_files, config_files)
        scal = self._score_scalability(parsed_files, config_files, folder_structure)

        scores = [cq["score"], pr["score"], sec["score"], scal["score"]]
        overall = round(sum(scores) / len(scores), 1)

        # Time-to-understand estimate
        total_lines = sum(pf["line_count"] for pf in parsed_files)
        total_files = len(parsed_files)
        total_functions = sum(len(pf["functions"]) for pf in parsed_files)
        complexity_factor = 1.0
        if total_files > 100:
            complexity_factor = 1.5
        if total_files > 500:
            complexity_factor = 2.5
        minutes = int((total_files * 0.5 + total_functions * 0.2 + total_lines * 0.005) * complexity_factor)
        if minutes < 10:
            time_est = f"~{minutes} minutes"
        elif minutes < 120:
            time_est = f"~{minutes} minutes"
        else:
            time_est = f"~{minutes // 60} hours"

        return {
            "overall_score": overall,
            "code_quality": cq,
            "production_readiness": pr,
            "security": sec,
            "scalability": scal,
            "time_to_understand": time_est,
            "stats": {
                "total_files": total_files,
                "total_lines": total_lines,
                "total_functions": total_functions,
                "languages": list(set(pf["language"] for pf in parsed_files)),
            },
        }

    def _score_code_quality(self, parsed_files: list[dict]) -> dict:
        """Score based on SOLID indicators, modularity, naming."""
        score = 10.0
        details = []
        issues = []

        # 1. Average function length (shorter = better)
        all_funcs = []
        for pf in parsed_files:
            for func in pf["functions"]:
                body_lines = func["body"].count("\n") + 1
                all_funcs.append({"name": func["name"], "lines": body_lines, "file": func["file_path"]})

        if all_funcs:
            avg_len = sum(f["lines"] for f in all_funcs) / len(all_funcs)
            long_funcs = [f for f in all_funcs if f["lines"] > 50]
            very_long = [f for f in all_funcs if f["lines"] > 100]

            if avg_len > 40:
                score -= 2.0
                issues.append(f"Average function length is {avg_len:.0f} lines — consider breaking down")
            elif avg_len > 25:
                score -= 1.0
                issues.append(f"Average function length is {avg_len:.0f} lines — slightly long")
            else:
                details.append(f"Average function length: {avg_len:.0f} lines — good")

            if very_long:
                score -= 1.5
                names = [f"{f['name']} ({f['lines']}L)" for f in very_long[:5]]
                issues.append(f"Very long functions (>100 lines): {', '.join(names)}")
            elif long_funcs:
                score -= 0.5
                details.append(f"{len(long_funcs)} functions over 50 lines")
        else:
            details.append("No functions detected")

        # 2. Naming consistency (snake_case vs camelCase mix)
        snake = sum(1 for f in all_funcs if re.match(r'^[a-z_][a-z0-9_]*$', f["name"]))
        camel = sum(1 for f in all_funcs if re.match(r'^[a-z][a-zA-Z0-9]*$', f["name"]) and '_' not in f["name"])
        if all_funcs:
            total = len(all_funcs)
            dominant = max(snake, camel)
            consistency = dominant / total if total > 0 else 1.0
            if consistency < 0.7:
                score -= 1.0
                issues.append(f"Inconsistent naming: {snake} snake_case, {camel} camelCase")
            else:
                details.append("Naming convention is consistent")

        # 3. File size distribution
        large_files = [pf for pf in parsed_files if pf["line_count"] > 500]
        if large_files:
            score -= min(1.5, len(large_files) * 0.3)
            names = [pf["file_path"] for pf in large_files[:5]]
            issues.append(f"Large files (>500 lines): {', '.join(names)}")
        else:
            details.append("No excessively large files")

        # 4. Module separation (files per directory)
        dirs = {}
        for pf in parsed_files:
            parent = str(Path(pf["file_path"]).parent)
            dirs[parent] = dirs.get(parent, 0) + 1
        crowded = {d: c for d, c in dirs.items() if c > 20}
        if crowded:
            score -= 1.0
            issues.append(f"Crowded directories: {', '.join(f'{d} ({c} files)' for d, c in list(crowded.items())[:3])}")
        else:
            details.append("Good directory organization")

        # 5. Docstrings/comments ratio (for Python)
        py_files = [pf for pf in parsed_files if pf["language"] == "python"]
        if py_files:
            documented = 0
            for pf in py_files:
                for func in pf["functions"]:
                    if '"""' in func["body"][:200] or "'''" in func["body"][:200]:
                        documented += 1
            py_funcs = sum(len(pf["functions"]) for pf in py_files)
            if py_funcs > 0:
                doc_ratio = documented / py_funcs
                if doc_ratio < 0.2:
                    score -= 0.5
                    issues.append(f"Low documentation: only {doc_ratio:.0%} of Python functions have docstrings")
                elif doc_ratio > 0.5:
                    details.append(f"{doc_ratio:.0%} of Python functions documented")

        return {
            "score": round(max(0, min(10, score)), 1),
            "details": details,
            "issues": issues,
        }

    def _score_production_readiness(self, parsed_files: list[dict], config_files: dict) -> dict:
        """Score logging, error handling, config management, CI/CD, Docker."""
        score = 0.0
        details = []
        issues = []

        all_source = "\n".join(pf.get("source_preview", "") for pf in parsed_files)
        config_names = set(config_files.keys())

        # 1. Logging (2 pts)
        has_logging = any(
            kw in all_source for kw in ["logging.", "logger.", "console.log", "log.", "Log.", "slog."]
        )
        if has_logging:
            score += 2.0
            details.append("Logging detected")
        else:
            issues.append("No logging framework detected")

        # 2. Error handling (2 pts)
        error_patterns = ["try:", "except", "try {", "catch", ".catch(", "rescue", "recover"]
        error_count = sum(1 for pat in error_patterns if pat in all_source)
        if error_count >= 3:
            score += 2.0
            details.append("Error handling present across codebase")
        elif error_count >= 1:
            score += 1.0
            issues.append("Limited error handling")
        else:
            issues.append("No error handling detected")

        # 3. Config management (2 pts)
        config_indicators = [".env", "dotenv", "config.", "settings.", "os.environ", "process.env"]
        has_config = any(kw in all_source or any(kw in n for n in config_names) for kw in config_indicators)
        if has_config:
            score += 2.0
            details.append("Configuration management detected")
        else:
            issues.append("No configuration management detected")

        # 4. Docker/CI/CD (2 pts)
        has_docker = any("dockerfile" in n.lower() or "docker-compose" in n.lower() for n in config_names)
        has_ci = any(".github/workflows" in n or "Jenkinsfile" in n or ".gitlab-ci" in n for n in config_names)
        if has_docker:
            score += 1.0
            details.append("Docker configuration found")
        else:
            issues.append("No Docker configuration")
        if has_ci:
            score += 1.0
            details.append("CI/CD pipeline detected")
        else:
            issues.append("No CI/CD pipeline detected")

        # 5. Testing (2 pts)
        test_files = [pf for pf in parsed_files if "test" in pf["file_path"].lower() or "spec" in pf["file_path"].lower()]
        if test_files:
            ratio = len(test_files) / max(1, len(parsed_files))
            if ratio > 0.15:
                score += 2.0
                details.append(f"Good test coverage: {len(test_files)} test files ({ratio:.0%})")
            else:
                score += 1.0
                issues.append(f"Low test coverage: {len(test_files)} test files ({ratio:.0%})")
        else:
            issues.append("No test files detected")

        return {
            "score": round(max(0, min(10, score)), 1),
            "details": details,
            "issues": issues,
        }

    def _score_security(self, parsed_files: list[dict], config_files: dict) -> dict:
        """Score secrets, input validation, auth patterns."""
        score = 10.0
        details = []
        issues = []

        all_source = "\n".join(pf.get("source_preview", "") for pf in parsed_files)
        config_content = "\n".join(config_files.values())

        # 1. Hardcoded secrets
        secret_patterns = [
            (r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']{3,}["\']', "Hardcoded password detected"),
            (r'(?:api_key|apikey|api-key)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded API key detected"),
            (r'(?:secret|token)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded secret/token detected"),
            (r'(?:aws_access_key|aws_secret)\s*=\s*["\'][^"\']{8,}["\']', "AWS credentials hardcoded"),
        ]
        for pattern, msg in secret_patterns:
            if re.search(pattern, all_source, re.IGNORECASE):
                score -= 2.5
                issues.append(msg)

        # Also check config files
        for pattern, msg in secret_patterns:
            if re.search(pattern, config_content, re.IGNORECASE):
                score -= 1.5
                issues.append(f"{msg} (in config files)")

        # 2. Input validation
        validation_patterns = ["validate", "sanitize", "escape", "parameterized", "prepared"]
        has_validation = any(v in all_source.lower() for v in validation_patterns)
        if has_validation:
            details.append("Input validation patterns detected")
        else:
            score -= 1.0
            issues.append("No input validation/sanitization detected")

        # 3. SQL injection risk
        raw_sql_patterns = [
            r'f["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*\{',
            r'(?:execute|query)\s*\(\s*f["\']',
            r'\.format\(.*(?:SELECT|INSERT|UPDATE|DELETE)',
        ]
        for pattern in raw_sql_patterns:
            if re.search(pattern, all_source, re.IGNORECASE):
                score -= 2.0
                issues.append("Potential SQL injection: string interpolation in SQL queries")
                break

        # 4. CORS / security headers
        if "cors" in all_source.lower() or "CORS" in all_source:
            details.append("CORS configuration detected")
        else:
            score -= 0.5
            issues.append("No CORS configuration detected")

        # 5. .env in .gitignore
        config_names = set(config_files.keys())
        gitignore = config_files.get(".gitignore", "")
        if ".env" in gitignore:
            details.append(".env excluded from git")
        elif any(".env" in n for n in config_names):
            score -= 1.0
            issues.append(".env file may be committed to repository")

        if not issues:
            details.append("No obvious security issues found")

        return {
            "score": round(max(0, min(10, score)), 1),
            "details": details,
            "issues": issues,
        }

    def _score_scalability(self, parsed_files: list[dict], config_files: dict, folder_structure: dict) -> dict:
        """Score stateless design, DB patterns, caching, async."""
        score = 5.0  # Start at middle
        details = []
        issues = []

        all_source = "\n".join(pf.get("source_preview", "") for pf in parsed_files)
        config_content = "\n".join(config_files.values())

        # 1. Async support (+2)
        async_patterns = ["async def", "async function", "await ", "Promise", "CompletableFuture"]
        if any(p in all_source for p in async_patterns):
            score += 2.0
            details.append("Async/await patterns detected — supports concurrent operations")
        else:
            issues.append("No async patterns detected — may limit concurrency")

        # 2. Caching (+1)
        cache_patterns = ["cache", "redis", "memcache", "lru_cache", "@cache"]
        if any(p in all_source.lower() or p in config_content.lower() for p in cache_patterns):
            score += 1.0
            details.append("Caching mechanisms detected")
        else:
            issues.append("No caching layer detected")

        # 3. Database connection pooling (+1)
        pool_patterns = ["pool", "connection_pool", "pool_size", "max_connections"]
        if any(p in all_source.lower() or p in config_content.lower() for p in pool_patterns):
            score += 1.0
            details.append("Database connection pooling detected")

        # 4. Global mutable state (-2)
        global_state = all_source.count("global ") + all_source.count("_instance = None")
        if global_state > 5:
            score -= 2.0
            issues.append(f"Heavy global mutable state detected ({global_state} instances)")
        elif global_state > 0:
            score -= 0.5
            issues.append(f"Some global state detected ({global_state} instances)")

        # 5. Queue/message patterns (+1)
        queue_patterns = ["celery", "rabbitmq", "kafka", "queue", "pubsub", "sns", "sqs"]
        if any(p in all_source.lower() or p in config_content.lower() for p in queue_patterns):
            score += 1.0
            details.append("Message queue / async processing detected")

        # 6. Containerization bonus
        if any("docker" in n.lower() for n in config_files.keys()):
            score += 0.5
            details.append("Containerized deployment supports horizontal scaling")

        return {
            "score": round(max(0, min(10, score)), 1),
            "details": details,
            "issues": issues,
        }
