"""Agent tools — capabilities the AI agent can invoke to explore a codebase.

Each tool takes structured input and returns a string summary the LLM can reason about.
Tools operate on in-memory caches populated during analysis (parsed files, graphs, embeddings).
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AgentTools:
    """Provides tools for the agent to explore an analyzed codebase."""

    def __init__(
        self,
        parsed_files: list[dict],
        knowledge_graph,       # CodeKnowledgeGraph instance
        vector_store,          # VectorStore instance
        collection_name: str,
        analysis_result: dict,  # Full AnalysisResult dict
        hybrid_search=None,    # HybridSearchEngine instance (optional)
    ):
        self.parsed_files = parsed_files
        self.kg = knowledge_graph
        self.vs = vector_store
        self.collection_name = collection_name
        self.result = analysis_result
        self.hybrid = hybrid_search
        # Build quick lookup indexes
        self._file_index = {pf["file_path"]: pf for pf in parsed_files}
        self._func_index = {}
        for pf in parsed_files:
            for func in pf["functions"]:
                key = f"{func['file_path']}::{func['name']}"
                self._func_index[key] = func

    # ==================== TOOL DEFINITIONS ====================
    # Each tool returns (tool_name, result_string)

    TOOL_DESCRIPTIONS = {
        "search_files": "Search for files by name pattern or keyword. Input: query string (e.g., 'auth', 'login', 'database')",
        "read_file": "Read the source code of a specific file. Input: file path",
        "search_code": "Semantic search across the codebase using embeddings. Input: natural language query",
        "find_functions": "Find functions by name pattern. Input: function name or keyword",
        "read_function": "Read a specific function's source code. Input: 'file_path::function_name'",
        "trace_dependencies": "Find what depends on a file or function. Input: file path or 'file_path::func_name'",
        "trace_flow": "Trace execution flow between two code elements. Input: 'source -> target' (node IDs)",
        "get_module_info": "Get info about a module/directory. Input: module name",
        "get_analysis_section": "Get a pre-computed analysis section. Input: section name (overview, tech_stack, security, modules, etc.)",
    }

    def get_tool_descriptions_prompt(self) -> str:
        """Format tool descriptions for inclusion in the LLM prompt."""
        lines = []
        for name, desc in self.TOOL_DESCRIPTIONS.items():
            lines.append(f"  - {name}: {desc}")
        return "\n".join(lines)

    async def execute_tool(self, tool_name: str, tool_input: str) -> str:
        """Execute a tool by name and return its output as a string."""
        tool_input = tool_input.strip()
        try:
            if tool_name == "search_files":
                return self.search_files(tool_input)
            elif tool_name == "read_file":
                return self.read_file(tool_input)
            elif tool_name == "search_code":
                return self.search_code(tool_input)
            elif tool_name == "find_functions":
                return self.find_functions(tool_input)
            elif tool_name == "read_function":
                return self.read_function(tool_input)
            elif tool_name == "trace_dependencies":
                return self.trace_dependencies(tool_input)
            elif tool_name == "trace_flow":
                return self.trace_flow(tool_input)
            elif tool_name == "get_module_info":
                return self.get_module_info(tool_input)
            elif tool_name == "get_analysis_section":
                return self.get_analysis_section(tool_input)
            else:
                return f"Unknown tool: {tool_name}. Available tools: {', '.join(self.TOOL_DESCRIPTIONS.keys())}"
        except Exception as e:
            logger.warning(f"Tool {tool_name} failed: {e}")
            return f"Tool error: {e}"

    # ==================== TOOL IMPLEMENTATIONS ====================

    def search_files(self, query: str) -> str:
        """Search files by name/path pattern."""
        query_lower = query.lower()
        matches = []
        for pf in self.parsed_files:
            fp = pf["file_path"]
            if query_lower in fp.lower():
                funcs = [f["name"] for f in pf["functions"]]
                matches.append(
                    f"  {fp} ({pf['language']}, {pf['line_count']}L, {len(funcs)} funcs)"
                    f" — functions: {funcs[:8]}"
                )

        if not matches:
            return f"No files matching '{query}'. Total files: {len(self.parsed_files)}"
        return f"Found {len(matches)} files matching '{query}':\n" + "\n".join(matches[:15])

    def read_file(self, file_path: str) -> str:
        """Read a file's source code."""
        file_path = file_path.strip().strip("'\"")
        pf = self._file_index.get(file_path)
        if not pf:
            # Try partial match
            for fp, data in self._file_index.items():
                if file_path in fp:
                    pf = data
                    file_path = fp
                    break
        if not pf:
            return f"File not found: {file_path}. Use search_files to find the correct path."

        source = pf.get("source_preview", "")
        funcs = [f["name"] for f in pf["functions"]]
        header = (
            f"File: {file_path}\n"
            f"Language: {pf['language']}, Lines: {pf['line_count']}\n"
            f"Functions: {funcs}\n"
            f"---\n"
        )
        # Truncate very long files
        if len(source) > 2000:
            source = source[:2000] + "\n... (truncated)"
        return header + source

    def search_code(self, query: str) -> str:
        """Hybrid search (BM25 + vector) with re-ranking."""
        results = []
        method = "vector"

        # Use hybrid search if available
        if self.hybrid:
            results = self.hybrid.search(query, n_results=4)
            method = "hybrid"

        # Fallback to vector-only
        if not results:
            results = self.vs.query(query, n_results=4, collection_name=self.collection_name)

        if not results:
            return f"No relevant code found for: '{query}'"

        parts = []
        for r in results:
            meta = r.get("metadata", {})
            chunk_type = meta.get("chunk_type", "?")
            # Show relevance info
            if "rrf_score" in r:
                score_info = f"RRF:{r['rrf_score']:.4f}"
                sources = "+".join(r.get("sources", []))
                score_info += f" ({sources})"
            elif "distance" in r:
                relevance = max(0, round((1 - r["distance"]) * 100))
                score_info = f"{relevance}%"
            else:
                score_info = "?"
            content = r.get("content", "")
            if len(content) > 500:
                content = content[:500] + "..."
            parts.append(
                f"  [{score_info}] {meta.get('file_path', '?')} "
                f"({chunk_type}, L{meta.get('start_line', '?')}-{meta.get('end_line', '?')}):\n{content}"
            )
        return f"Search results for '{query}' ({method}):\n" + "\n\n".join(parts)

    def find_functions(self, query: str) -> str:
        """Find functions by name pattern."""
        query_lower = query.lower()
        matches = []
        for pf in self.parsed_files:
            for func in pf["functions"]:
                if query_lower in func["name"].lower():
                    body_lines = func["body"].count("\n") + 1
                    params = func.get("parameters", [])
                    matches.append(
                        f"  {func['name']}({', '.join(params[:5])}) "
                        f"in {func['file_path']} "
                        f"(L{func['start_line']}-{func['end_line']}, {body_lines}L)"
                    )
        if not matches:
            return f"No functions matching '{query}'."
        return f"Found {len(matches)} functions matching '{query}':\n" + "\n".join(matches[:15])

    def read_function(self, key: str) -> str:
        """Read a function's full source. Input: 'file_path::function_name' or just 'function_name'."""
        if "::" in key:
            func = self._func_index.get(key)
            if func:
                return f"Function: {func['name']}\nFile: {func['file_path']}\nLines: {func['start_line']}-{func['end_line']}\n---\n{func['body'][:1500]}"
        # Try to find by name alone
        name_lower = key.lower().strip()
        for fkey, func in self._func_index.items():
            if func["name"].lower() == name_lower:
                return f"Function: {func['name']}\nFile: {func['file_path']}\nLines: {func['start_line']}-{func['end_line']}\n---\n{func['body'][:1500]}"
        return f"Function not found: {key}. Use find_functions to search."

    def trace_dependencies(self, target: str) -> str:
        """Trace what depends on a file or function."""
        if not self.kg or not self.kg.graph:
            return "Knowledge graph not available."

        # Try as file
        node_id = f"file::{target}"
        if not self.kg.graph.has_node(node_id):
            # Try as function
            node_id = f"func::{target}"
        if not self.kg.graph.has_node(node_id):
            # Search by name
            results = self.kg.search_nodes(target)
            if results:
                node_id = results[0]["node_id"]
            else:
                return f"Node not found for '{target}'. Use search_files or find_functions first."

        deps = self.kg.get_dependents(node_id, depth=2)
        direct = deps.get("direct", [])
        indirect = deps.get("indirect", [])

        parts = [f"Dependencies for {node_id}:"]
        if direct:
            parts.append(f"\nDirect dependents ({len(direct)}):")
            for d in direct[:10]:
                parts.append(f"  <- {d['node']} (via {d['via']})")
        if indirect:
            parts.append(f"\nIndirect dependents ({len(indirect)}):")
            for d in indirect[:10]:
                parts.append(f"  <-- {d['node']} (via {d['via']}, depth {d['depth']})")
        if not direct and not indirect:
            parts.append("  No dependents found.")
        return "\n".join(parts)

    def trace_flow(self, input_str: str) -> str:
        """Trace execution flow between two nodes. Input: 'source -> target'."""
        if not self.kg or not self.kg.graph:
            return "Knowledge graph not available."

        parts = input_str.split("->")
        if len(parts) != 2:
            return "Invalid format. Use: 'source_node -> target_node'"

        source = parts[0].strip()
        target = parts[1].strip()

        # Resolve names to node IDs
        def resolve(name: str) -> Optional[str]:
            for prefix in ["file::", "func::", "class::", "module::"]:
                candidate = f"{prefix}{name}"
                if self.kg.graph.has_node(candidate):
                    return candidate
            results = self.kg.search_nodes(name)
            return results[0]["node_id"] if results else None

        src_id = resolve(source)
        tgt_id = resolve(target)

        if not src_id:
            return f"Source not found: '{source}'"
        if not tgt_id:
            return f"Target not found: '{target}'"

        trace = self.kg.trace_path(src_id, tgt_id)
        if trace.get("error"):
            return f"No path found: {trace['error']}"

        shortest = trace.get("shortest_path", [])
        total = trace.get("total_paths", 0)
        result = f"Flow from {src_id} to {tgt_id}:\n"
        result += f"Shortest path ({len(shortest)} steps): {' -> '.join(shortest)}\n"
        result += f"Total paths found: {total}"
        return result

    def get_module_info(self, module_name: str) -> str:
        """Get info about a module/directory."""
        module_lower = module_name.lower().strip()
        matches = []
        for pf in self.parsed_files:
            parts = pf["file_path"].split("/")
            if len(parts) > 1 and module_lower in parts[0].lower():
                matches.append(pf)
            elif module_lower in pf["file_path"].lower():
                matches.append(pf)

        if not matches:
            return f"Module '{module_name}' not found."

        total_lines = sum(m["line_count"] for m in matches)
        total_funcs = sum(len(m["functions"]) for m in matches)
        languages = list(set(m["language"] for m in matches))
        files = [m["file_path"] for m in matches]

        return (
            f"Module: {module_name}\n"
            f"Files: {len(matches)}\n"
            f"Total lines: {total_lines}\n"
            f"Total functions: {total_funcs}\n"
            f"Languages: {languages}\n"
            f"Files:\n" + "\n".join(f"  {f}" for f in files[:20])
        )

    def get_analysis_section(self, section: str) -> str:
        """Get a pre-computed analysis section."""
        import json
        section = section.lower().strip()
        mapping = {
            "overview": "repo_overview",
            "tech_stack": "tech_stack",
            "tech": "tech_stack",
            "modules": "modules",
            "security": "security_analysis",
            "production": "production_readiness",
            "health": "health_dashboard",
            "dependencies": "dependencies",
            "flow": "system_flow",
            "cost": "cost_analysis",
            "quality": "code_quality",
            "knowledge_graph": "knowledge_graph",
            "recommendations": "recommendations",
        }
        key = mapping.get(section, section)
        data = self.result.get(key)
        if data is None:
            available = [k for k, v in self.result.items() if v is not None and k not in ("job_id", "repo_url", "branch", "status")]
            return f"Section '{section}' not available. Available: {available}"

        text = json.dumps(data, indent=2, default=str)
        if len(text) > 1500:
            text = text[:1500] + "\n... (truncated)"
        return f"Analysis section '{section}':\n{text}"
