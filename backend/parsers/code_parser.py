"""Code parsing using Tree-sitter and Python AST for function/class extraction."""
import ast
import re
from pathlib import Path
from backend.models.schemas import FunctionInfo, CodeChunk
from backend.utils.helpers import detect_language, chunk_id, read_file_safe, truncate


class PythonASTParser:
    """Deep parser for Python using built-in AST module."""

    def extract_functions(self, file_path: str, source: str) -> list[FunctionInfo]:
        functions = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return functions

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                params = []
                for arg in node.args.args:
                    params.append(arg.arg)

                start = node.lineno
                end = node.end_lineno or start
                lines = source.splitlines()
                body = "\n".join(lines[start - 1:end])

                functions.append(FunctionInfo(
                    name=node.name,
                    file_path=file_path,
                    start_line=start,
                    end_line=end,
                    parameters=params,
                    body=truncate(body, 3000),
                    language="python",
                ))
        return functions

    def extract_classes(self, source: str) -> list[dict]:
        classes = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return classes

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [
                    n.name for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(ast.dump(base))

                classes.append({
                    "name": node.name,
                    "methods": methods,
                    "bases": bases,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                })
        return classes

    def extract_imports(self, source: str) -> list[str]:
        imports = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return imports

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        return imports


class GenericParser:
    """Regex-based parser for non-Python languages."""

    FUNCTION_PATTERNS = {
        "javascript": r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)',
        "typescript": r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*(?:<[^>]*>)?\s*\(([^)]*)\)',
        "java": r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(([^)]*)\)',
        "go": r'func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(([^)]*)\)',
        "rust": r'(?:pub\s+)?fn\s+(\w+)\s*(?:<[^>]*>)?\s*\(([^)]*)\)',
        "ruby": r'def\s+(\w+)(?:\(([^)]*)\))?',
        "php": r'(?:public|private|protected)?\s*function\s+(\w+)\s*\(([^)]*)\)',
        "csharp": r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(([^)]*)\)',
    }

    IMPORT_PATTERNS = {
        "javascript": r'(?:import\s+.*?from\s+[\'"]([^\'"]+)[\'"]|require\s*\([\'"]([^\'"]+)[\'"]\))',
        "typescript": r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]',
        "java": r'import\s+([\w.]+)',
        "go": r'import\s+(?:\(\s*([\s\S]*?)\s*\)|"([^"]+)")',
        "rust": r'use\s+([\w:]+)',
        "ruby": r'require\s+[\'"]([^\'"]+)[\'"]',
        "php": r'(?:use|require|include)\s+([^\s;]+)',
        "csharp": r'using\s+([\w.]+)',
    }

    def extract_functions(self, file_path: str, source: str, language: str) -> list[FunctionInfo]:
        pattern = self.FUNCTION_PATTERNS.get(language)
        if not pattern:
            return []

        functions = []
        lines = source.splitlines()
        for match in re.finditer(pattern, source):
            name = match.group(1)
            params_str = match.group(2) if match.lastindex >= 2 else ""
            params = [p.strip().split()[-1] for p in params_str.split(",") if p.strip()] if params_str else []

            start_pos = match.start()
            start_line = source[:start_pos].count("\n") + 1

            # Estimate function end by finding the matching closing brace
            end_line = min(start_line + 50, len(lines))
            brace_count = 0
            found_open = False
            for i in range(start_line - 1, min(start_line + 200, len(lines))):
                line = lines[i]
                brace_count += line.count("{") - line.count("}")
                if "{" in line:
                    found_open = True
                if found_open and brace_count <= 0:
                    end_line = i + 1
                    break

            body = "\n".join(lines[start_line - 1:end_line])

            functions.append(FunctionInfo(
                name=name,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                parameters=params,
                body=truncate(body, 3000),
                language=language,
            ))
        return functions

    def extract_imports(self, source: str, language: str) -> list[str]:
        pattern = self.IMPORT_PATTERNS.get(language)
        if not pattern:
            return []

        imports = []
        for match in re.finditer(pattern, source):
            for group in match.groups():
                if group:
                    imports.append(group.strip())
        return imports


class CodeParser:
    """Unified code parser that dispatches to language-specific parsers."""

    def __init__(self):
        self.python_parser = PythonASTParser()
        self.generic_parser = GenericParser()

    def parse_file(self, file_path: Path, repo_root: Path) -> dict:
        source = read_file_safe(file_path)
        if not source.strip():
            return None

        rel_path = str(file_path.relative_to(repo_root))
        language = detect_language(str(file_path))
        lines = source.splitlines()

        # Extract functions
        if language == "python":
            functions = self.python_parser.extract_functions(rel_path, source)
            imports = self.python_parser.extract_imports(source)
            classes = self.python_parser.extract_classes(source)
        else:
            functions = self.generic_parser.extract_functions(rel_path, source, language)
            imports = self.generic_parser.extract_imports(source, language)
            classes = []

        # Build chunks
        chunks = []

        # File-level chunk
        chunks.append(CodeChunk(
            chunk_id=chunk_id(rel_path, 0, "file"),
            file_path=rel_path,
            chunk_type="file",
            content=truncate(source, 4000),
            language=language,
            start_line=1,
            end_line=len(lines),
            metadata={"imports": imports},
        ))

        # Function-level chunks
        for func in functions:
            chunks.append(CodeChunk(
                chunk_id=chunk_id(rel_path, func.start_line, "function"),
                file_path=rel_path,
                chunk_type="function",
                content=func.body,
                language=language,
                start_line=func.start_line,
                end_line=func.end_line,
                metadata={"function_name": func.name, "parameters": func.parameters},
            ))

        return {
            "file_path": rel_path,
            "language": language,
            "line_count": len(lines),
            "size_bytes": len(source.encode()),
            "functions": [f.model_dump() for f in functions],
            "classes": classes if language == "python" else [],
            "imports": imports,
            "chunks": chunks,
            "source_preview": truncate(source, 2000),
        }

    def parse_repo(self, repo_path: Path, files: list[Path]) -> list[dict]:
        results = []
        for f in files:
            parsed = self.parse_file(f, repo_path)
            if parsed:
                results.append(parsed)
        return results
