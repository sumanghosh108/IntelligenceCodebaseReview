"""Code Quality Intelligence — hybrid rule-based + AI evaluator.

Rule-based checks (pylint/flake8 style):
  - Cyclomatic complexity estimation
  - Dead code detection (unused imports, unreachable code)
  - Naming convention violations
  - Code duplication patterns
  - Anti-patterns (god classes, long parameter lists, deep nesting)
  - Import hygiene

AI-based checks (via LLM):
  - Architecture critique (coupling, cohesion, layering violations)
  - Design flaw detection (missing abstractions, leaky interfaces)
  - Pattern violations (SOLID, DRY, separation of concerns)

Output: list of {"issue", "impact", "fix", "severity", "category", "file", "line"}
"""
import re
import ast
import logging
from pathlib import Path
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

# Severity levels
CRITICAL = "critical"
HIGH = "high"
MEDIUM = "medium"
LOW = "low"

# Categories
CAT_COMPLEXITY = "complexity"
CAT_NAMING = "naming"
CAT_DUPLICATION = "duplication"
CAT_DEAD_CODE = "dead_code"
CAT_ANTI_PATTERN = "anti_pattern"
CAT_IMPORT = "import_hygiene"
CAT_ARCHITECTURE = "architecture"
CAT_DESIGN = "design"


class CodeQualityAnalyzer:
    """Hybrid rule-based + AI code quality evaluator."""

    def analyze_rule_based(self, parsed_files: list[dict]) -> list[dict]:
        """Run all rule-based checks across parsed files. Returns issue list."""
        issues = []
        issues.extend(self._check_complexity(parsed_files))
        issues.extend(self._check_naming(parsed_files))
        issues.extend(self._check_duplication(parsed_files))
        issues.extend(self._check_dead_code(parsed_files))
        issues.extend(self._check_anti_patterns(parsed_files))
        issues.extend(self._check_import_hygiene(parsed_files))
        return issues

    def build_ai_prompt(self, parsed_files: list[dict], rule_issues: list[dict]) -> str:
        """Build prompt for LLM architecture/design critique."""
        # Summarize codebase structure
        file_summaries = []
        for pf in parsed_files[:30]:
            funcs = [f["name"] for f in pf["functions"]]
            file_summaries.append(
                f"  {pf['file_path']} ({pf['language']}, {pf['line_count']}L) "
                f"functions: {funcs}"
            )
        structure = "\n".join(file_summaries)

        # Summarize rule-based findings
        rule_summary = ""
        if rule_issues:
            by_cat = defaultdict(list)
            for iss in rule_issues:
                by_cat[iss["category"]].append(iss["issue"])
            parts = []
            for cat, items in by_cat.items():
                parts.append(f"  {cat}: {len(items)} issues (e.g., {items[0]})")
            rule_summary = "\n".join(parts)

        # Code samples from important files
        code_samples = []
        for pf in parsed_files[:10]:
            preview = pf.get("source_preview", "")
            if preview:
                code_samples.append(f"--- {pf['file_path']} ---\n{preview[:1500]}")
        code_context = "\n\n".join(code_samples)

        return f"""Analyze this codebase for architecture and design quality issues.
Focus on issues that static analysis CANNOT detect: coupling, cohesion, layering violations,
missing abstractions, SOLID violations, and design flaws.

Codebase structure:
{structure}

Rule-based findings already detected:
{rule_summary if rule_summary else "  (none)"}

Code samples:
{code_context[:5000]}

Return a JSON array of issues. Each issue MUST have exactly these fields:
[
  {{
    "issue": "short description of the problem",
    "impact": "what happens if not fixed (e.g., low scalability, hard to test)",
    "fix": "concrete actionable fix (e.g., introduce service abstraction layer)",
    "severity": "critical|high|medium|low",
    "category": "architecture|design",
    "file": "affected file path or 'codebase-wide'",
    "line": null
  }}
]

Rules:
- Return 3-8 issues, focusing on the most impactful ones
- Do NOT repeat issues already found by rule-based analysis
- Focus on structural/design problems, not style issues
- Be specific: name actual files, modules, and patterns
- "fix" must be actionable, not vague ("add tests" is bad, "add integration test for X payment flow" is good)

Respond with ONLY the JSON array, no other text."""

    def merge_results(
        self, rule_issues: list[dict], ai_issues: list[dict]
    ) -> dict:
        """Merge rule-based and AI issues into final report."""
        all_issues = rule_issues + ai_issues

        # Deduplicate by similarity (simple check)
        seen_keys = set()
        deduped = []
        for iss in all_issues:
            key = (iss.get("file", ""), iss.get("category", ""), iss["issue"][:50])
            if key not in seen_keys:
                seen_keys.add(key)
                deduped.append(iss)

        # Sort: critical first, then high, medium, low
        severity_order = {CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3}
        deduped.sort(key=lambda x: severity_order.get(x.get("severity", LOW), 3))

        # Aggregate stats
        by_severity = Counter(iss.get("severity", LOW) for iss in deduped)
        by_category = Counter(iss.get("category", "other") for iss in deduped)

        # Calculate quality score (10 = perfect, deduct for issues)
        score = 10.0
        for iss in deduped:
            sev = iss.get("severity", LOW)
            if sev == CRITICAL:
                score -= 1.5
            elif sev == HIGH:
                score -= 1.0
            elif sev == MEDIUM:
                score -= 0.5
            elif sev == LOW:
                score -= 0.2
        score = round(max(0, min(10, score)), 1)

        return {
            "score": score,
            "total_issues": len(deduped),
            "by_severity": dict(by_severity),
            "by_category": dict(by_category),
            "rule_based_count": len(rule_issues),
            "ai_detected_count": len(ai_issues),
            "issues": deduped,
        }

    # ===================== Rule-Based Checks =====================

    def _check_complexity(self, parsed_files: list[dict]) -> list[dict]:
        """Estimate cyclomatic complexity and flag overly complex functions."""
        issues = []
        for pf in parsed_files:
            for func in pf["functions"]:
                body = func["body"]
                # Estimate complexity: count decision points
                complexity = 1  # base
                decision_keywords = [
                    r'\bif\b', r'\belif\b', r'\belse\b', r'\bfor\b', r'\bwhile\b',
                    r'\bexcept\b', r'\bcatch\b', r'\bcase\b', r'\b\?\b',
                    r'\band\b', r'\bor\b', r'\b&&\b', r'\b\|\|\b',
                ]
                for kw in decision_keywords:
                    complexity += len(re.findall(kw, body))

                body_lines = body.count("\n") + 1

                if complexity > 20:
                    issues.append({
                        "issue": f"Function `{func['name']}` has very high complexity (~{complexity})",
                        "impact": "Hard to test, maintain, and debug; high bug density",
                        "fix": f"Break `{func['name']}` into smaller functions, each handling one responsibility",
                        "severity": CRITICAL if complexity > 30 else HIGH,
                        "category": CAT_COMPLEXITY,
                        "file": func["file_path"],
                        "line": func.get("start_line"),
                    })
                elif complexity > 12:
                    issues.append({
                        "issue": f"Function `{func['name']}` has moderate complexity (~{complexity})",
                        "impact": "Reduced readability and testability",
                        "fix": f"Extract helper functions from `{func['name']}` for nested conditions",
                        "severity": MEDIUM,
                        "category": CAT_COMPLEXITY,
                        "file": func["file_path"],
                        "line": func.get("start_line"),
                    })

                # Deep nesting check
                max_indent = 0
                for line in body.split("\n"):
                    stripped = line.lstrip()
                    if stripped:
                        indent = len(line) - len(stripped)
                        max_indent = max(max_indent, indent)
                # Normalize: 4 spaces = 1 level, tab = 1 level
                nesting_level = max_indent // 4 if max_indent > 0 else 0
                if nesting_level >= 5:
                    issues.append({
                        "issue": f"Function `{func['name']}` has deep nesting ({nesting_level} levels)",
                        "impact": "Arrow anti-pattern reduces readability",
                        "fix": "Use guard clauses (early returns) to flatten nesting",
                        "severity": MEDIUM,
                        "category": CAT_ANTI_PATTERN,
                        "file": func["file_path"],
                        "line": func.get("start_line"),
                    })
        return issues

    def _check_naming(self, parsed_files: list[dict]) -> list[dict]:
        """Check naming convention consistency and violations."""
        issues = []

        # Collect all function names per language
        by_lang: dict[str, list[dict]] = defaultdict(list)
        for pf in parsed_files:
            for func in pf["functions"]:
                by_lang[pf["language"]].append(func)

        for lang, funcs in by_lang.items():
            names = [f["name"] for f in funcs]
            if not names:
                continue

            # Check for single-char function names
            short_names = [f for f in funcs if len(f["name"]) <= 2 and f["name"] not in ("__", "_")]
            for f in short_names[:5]:
                issues.append({
                    "issue": f"Function `{f['name']}` has a non-descriptive name",
                    "impact": "Reduces code readability and self-documentation",
                    "fix": f"Rename `{f['name']}` to describe what it does",
                    "severity": LOW,
                    "category": CAT_NAMING,
                    "file": f["file_path"],
                    "line": f.get("start_line"),
                })

            # Check for overly long names (>40 chars)
            for f in funcs:
                if len(f["name"]) > 40:
                    issues.append({
                        "issue": f"Function name `{f['name'][:30]}...` is excessively long ({len(f['name'])} chars)",
                        "impact": "Reduces readability in call sites",
                        "fix": "Shorten the name while keeping it descriptive",
                        "severity": LOW,
                        "category": CAT_NAMING,
                        "file": f["file_path"],
                        "line": f.get("start_line"),
                    })

            # For Python: check for camelCase functions (should be snake_case)
            if lang == "python":
                camel_funcs = [
                    f for f in funcs
                    if re.match(r'^[a-z][a-zA-Z]+$', f["name"])
                    and '_' not in f["name"]
                    and any(c.isupper() for c in f["name"][1:])
                    and f["name"] not in ("setUp", "tearDown", "setUpClass", "tearDownClass")
                ]
                if camel_funcs and len(camel_funcs) >= 3:
                    issues.append({
                        "issue": f"{len(camel_funcs)} Python functions use camelCase instead of snake_case",
                        "impact": "Violates PEP 8 naming convention",
                        "fix": "Rename to snake_case (e.g., `getData` → `get_data`)",
                        "severity": LOW,
                        "category": CAT_NAMING,
                        "file": camel_funcs[0]["file_path"],
                        "line": None,
                    })

        return issues

    def _check_duplication(self, parsed_files: list[dict]) -> list[dict]:
        """Detect code duplication patterns."""
        issues = []

        # Strategy: hash normalized function bodies, find duplicates
        body_hashes: dict[str, list[dict]] = defaultdict(list)
        for pf in parsed_files:
            for func in pf["functions"]:
                body = func["body"].strip()
                if len(body) < 80:  # Skip trivial functions
                    continue
                # Normalize: strip whitespace, lowercase
                normalized = re.sub(r'\s+', ' ', body.lower())
                # Use first 200 chars as fingerprint (catches near-duplicates)
                fingerprint = normalized[:200]
                body_hashes[fingerprint].append({
                    "name": func["name"],
                    "file": func["file_path"],
                    "line": func.get("start_line"),
                    "lines": body.count("\n") + 1,
                })

        for fingerprint, matches in body_hashes.items():
            if len(matches) >= 2:
                names = [f"{m['name']} ({m['file']})" for m in matches[:4]]
                total_dup_lines = sum(m["lines"] for m in matches[1:])  # exclude original
                issues.append({
                    "issue": f"Near-duplicate code in {len(matches)} functions: {', '.join(names)}",
                    "impact": f"~{total_dup_lines} duplicated lines increase maintenance burden",
                    "fix": f"Extract shared logic into a common function",
                    "severity": HIGH if total_dup_lines > 50 else MEDIUM,
                    "category": CAT_DUPLICATION,
                    "file": matches[0]["file"],
                    "line": matches[0]["line"],
                })

        return issues

    def _check_dead_code(self, parsed_files: list[dict]) -> list[dict]:
        """Detect potentially unused/dead code patterns."""
        issues = []

        # Build a set of all function names defined
        all_defined = {}
        for pf in parsed_files:
            for func in pf["functions"]:
                all_defined[func["name"]] = {
                    "file": func["file_path"],
                    "line": func.get("start_line"),
                }

        # Build a set of all function names referenced in code
        all_source = ""
        for pf in parsed_files:
            all_source += pf.get("source_preview", "") + "\n"

        # Check which defined functions are never referenced elsewhere
        # (Simple heuristic — not perfect but catches obvious cases)
        potentially_unused = []
        for name, info in all_defined.items():
            # Skip special/magic methods and short names (likely used dynamically)
            if name.startswith("_") or len(name) <= 3:
                continue
            # Skip common patterns that are used dynamically (routes, handlers, tests)
            if any(kw in name.lower() for kw in ["test", "setup", "teardown", "main", "init"]):
                continue
            # Count references (excluding the definition itself)
            ref_count = len(re.findall(r'\b' + re.escape(name) + r'\b', all_source))
            if ref_count <= 1:  # Only the definition
                potentially_unused.append((name, info))

        if len(potentially_unused) >= 3:
            sample_names = [f"`{n}`" for n, _ in potentially_unused[:5]]
            issues.append({
                "issue": f"{len(potentially_unused)} potentially unused functions detected: {', '.join(sample_names)}",
                "impact": "Dead code increases cognitive load and maintenance cost",
                "fix": "Verify and remove unused functions, or add exports/references if they are used externally",
                "severity": MEDIUM if len(potentially_unused) > 10 else LOW,
                "category": CAT_DEAD_CODE,
                "file": potentially_unused[0][1]["file"],
                "line": None,
            })

        # Check for commented-out code blocks
        for pf in parsed_files:
            source = pf.get("source_preview", "")
            commented_code_lines = 0
            for line in source.split("\n"):
                stripped = line.strip()
                # Detect commented-out code (not regular comments)
                if (stripped.startswith("#") or stripped.startswith("//")) and any(
                    kw in stripped for kw in ["def ", "function ", "class ", "import ", "return ", "if ", "for "]
                ):
                    commented_code_lines += 1

            if commented_code_lines >= 5:
                issues.append({
                    "issue": f"~{commented_code_lines} lines of commented-out code in {pf['file_path']}",
                    "impact": "Clutters codebase, version control already tracks history",
                    "fix": "Remove commented-out code; use git history for recovery",
                    "severity": LOW,
                    "category": CAT_DEAD_CODE,
                    "file": pf["file_path"],
                    "line": None,
                })

        return issues

    def _check_anti_patterns(self, parsed_files: list[dict]) -> list[dict]:
        """Detect common anti-patterns."""
        issues = []

        for pf in parsed_files:
            source = pf.get("source_preview", "")
            file_path = pf["file_path"]

            # God class / god file: too many functions in one file
            func_count = len(pf["functions"])
            if func_count > 25:
                issues.append({
                    "issue": f"`{file_path}` has {func_count} functions — potential god module",
                    "impact": "Single Responsibility Principle violation; hard to navigate and test",
                    "fix": f"Split `{Path(file_path).name}` into smaller, focused modules",
                    "severity": HIGH if func_count > 40 else MEDIUM,
                    "category": CAT_ANTI_PATTERN,
                    "file": file_path,
                    "line": None,
                })

            # Long parameter lists
            for func in pf["functions"]:
                param_count = len(func.get("parameters", []))
                if param_count > 7:
                    issues.append({
                        "issue": f"Function `{func['name']}` has {param_count} parameters",
                        "impact": "Hard to call correctly, indicates function does too much",
                        "fix": f"Group related parameters into a dataclass/config object",
                        "severity": MEDIUM,
                        "category": CAT_ANTI_PATTERN,
                        "file": func["file_path"],
                        "line": func.get("start_line"),
                    })

            # Bare except / catch-all
            bare_except_count = len(re.findall(r'\bexcept\s*:', source))
            broad_except = len(re.findall(r'\bexcept\s+Exception\s*:', source))
            if bare_except_count + broad_except >= 3:
                issues.append({
                    "issue": f"{bare_except_count + broad_except} broad exception handlers in `{file_path}`",
                    "impact": "Silently swallows errors, making debugging difficult",
                    "fix": "Catch specific exceptions (e.g., `ValueError`, `KeyError`)",
                    "severity": MEDIUM,
                    "category": CAT_ANTI_PATTERN,
                    "file": file_path,
                    "line": None,
                })

            # Magic numbers (numeric literals that aren't 0, 1, 2)
            magic_numbers = re.findall(r'(?<!=\s)(?<!["\'])\b(\d{3,})\b(?!["\'])', source)
            # Filter out common non-magic numbers (ports, status codes, sizes)
            magic_numbers = [n for n in magic_numbers if int(n) not in {100, 200, 201, 204, 301, 302, 400, 401, 403, 404, 500, 1000, 1024, 3000, 5000, 8000, 8080}]
            if len(magic_numbers) >= 5:
                issues.append({
                    "issue": f"Multiple magic numbers in `{file_path}` (e.g., {', '.join(magic_numbers[:3])})",
                    "impact": "Unclear intent; changes require finding all occurrences",
                    "fix": "Extract magic numbers into named constants",
                    "severity": LOW,
                    "category": CAT_ANTI_PATTERN,
                    "file": file_path,
                    "line": None,
                })

        return issues

    def _check_import_hygiene(self, parsed_files: list[dict]) -> list[dict]:
        """Check import patterns for issues."""
        issues = []

        for pf in parsed_files:
            if pf["language"] != "python":
                continue

            source = pf.get("source_preview", "")
            file_path = pf["file_path"]

            # Wildcard imports
            wildcard_imports = re.findall(r'from\s+\S+\s+import\s+\*', source)
            if wildcard_imports:
                issues.append({
                    "issue": f"Wildcard import(s) in `{file_path}`: {wildcard_imports[0]}",
                    "impact": "Pollutes namespace, hides dependencies, breaks IDE support",
                    "fix": "Import specific names instead of using `*`",
                    "severity": MEDIUM,
                    "category": CAT_IMPORT,
                    "file": file_path,
                    "line": None,
                })

            # Circular import indicators (import inside function body)
            local_imports = re.findall(r'(?:def|async def)\s+\w+.*?(?:from\s+\S+\s+import|import\s+\S+)', source, re.DOTALL)
            # Simple heuristic: count import statements that appear after function defs
            func_level_imports = 0
            in_function = False
            for line in source.split("\n"):
                stripped = line.strip()
                if stripped.startswith("def ") or stripped.startswith("async def "):
                    in_function = True
                elif in_function and (stripped.startswith("import ") or stripped.startswith("from ")):
                    func_level_imports += 1

            if func_level_imports >= 3:
                issues.append({
                    "issue": f"{func_level_imports} function-level imports in `{file_path}` (possible circular dependency workaround)",
                    "impact": "Indicates architectural coupling; imports should be at module level",
                    "fix": "Resolve circular dependencies by restructuring modules or using dependency injection",
                    "severity": MEDIUM,
                    "category": CAT_IMPORT,
                    "file": file_path,
                    "line": None,
                })

        return issues
