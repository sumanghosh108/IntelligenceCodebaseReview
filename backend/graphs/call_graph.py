"""Call graph builder and impact analysis using NetworkX.

Builds function-level call graphs for:
- Call graph visualization
- Impact analysis ("what breaks if I change this?")
- Data flow tracking
"""
import re
import networkx as nx
from pathlib import Path


class CallGraphBuilder:
    """Builds function-level call graphs from parsed files."""

    def build(self, parsed_files: list[dict]) -> dict:
        """Build a function call graph from parsed file data."""
        G = nx.DiGraph()

        # Index all functions by name and qualified name
        func_index: dict[str, dict] = {}
        for pf in parsed_files:
            for func in pf["functions"]:
                qualified = f"{pf['file_path']}::{func['name']}"
                node_data = {
                    "name": func["name"],
                    "file": pf["file_path"],
                    "qualified": qualified,
                    "start_line": func["start_line"],
                    "end_line": func["end_line"],
                    "params": func.get("parameters", []),
                    "lines": func["end_line"] - func["start_line"] + 1,
                }
                G.add_node(qualified, **node_data)
                # Store by both simple and qualified name
                func_index[qualified] = node_data
                if func["name"] not in func_index:
                    func_index[func["name"]] = node_data

        # Build edges: scan each function body for calls to other known functions
        all_func_names = set()
        for pf in parsed_files:
            for func in pf["functions"]:
                all_func_names.add(func["name"])

        for pf in parsed_files:
            for func in pf["functions"]:
                caller = f"{pf['file_path']}::{func['name']}"
                body = func["body"]

                # Find function calls in body
                for other_name in all_func_names:
                    if other_name == func["name"]:
                        continue
                    # Look for function call pattern: name(
                    pattern = rf'\b{re.escape(other_name)}\s*\('
                    if re.search(pattern, body):
                        # Find the best matching callee
                        callee = self._resolve_callee(other_name, pf["file_path"], pf.get("imports", []), func_index)
                        if callee and callee != caller:
                            G.add_edge(caller, callee, type="call")

        # Compute metrics
        nodes = []
        for node, data in G.nodes(data=True):
            nodes.append({
                "id": node,
                "name": data.get("name", ""),
                "file": data.get("file", ""),
                "in_degree": G.in_degree(node),
                "out_degree": G.out_degree(node),
                "lines": data.get("lines", 0),
            })

        edges = [
            {"source": u, "target": v, "type": d.get("type", "call")}
            for u, v, d in G.edges(data=True)
        ]

        # Entry points (no callers)
        entry_points = [n for n in nodes if n["in_degree"] == 0 and n["out_degree"] > 0]

        # Hot functions (many callers)
        hot = sorted(nodes, key=lambda x: x["in_degree"], reverse=True)[:10]
        hot_functions = [n for n in hot if n["in_degree"] > 0]

        # Leaf functions (no outgoing calls)
        leaves = [n for n in nodes if n["out_degree"] == 0]

        return {
            "nodes": nodes,
            "edges": edges,
            "entry_points": [{"name": n["name"], "file": n["file"]} for n in entry_points],
            "hot_functions": [{"name": n["name"], "file": n["file"], "callers": n["in_degree"]} for n in hot_functions],
            "leaf_functions": [{"name": n["name"], "file": n["file"]} for n in leaves[:20]],
            "total_functions": len(nodes),
            "total_calls": len(edges),
        }

    def _resolve_callee(self, func_name: str, caller_file: str, imports: list[str], func_index: dict) -> str | None:
        """Resolve a function name to its qualified node ID."""
        # Try same-file first
        same_file_key = f"{caller_file}::{func_name}"
        if same_file_key in func_index:
            return same_file_key

        # Try by simple name (first match from any file)
        if func_name in func_index:
            info = func_index[func_name]
            return info.get("qualified", f"{info.get('file', '')}::{func_name}")

        return None


class ImpactAnalyzer:
    """Analyzes the impact of changing or removing a file or function."""

    def __init__(self):
        self.file_graph = None
        self.call_graph = None

    def set_graphs(self, file_dep_data: dict, call_graph_data: dict):
        """Initialize with pre-built graph data."""
        self.file_graph = nx.DiGraph()
        for node in file_dep_data.get("nodes", []):
            self.file_graph.add_node(node.get("file", node.get("id", "")))
        for edge in file_dep_data.get("edges", []):
            self.file_graph.add_edge(edge["source"], edge["target"])

        self.call_graph = nx.DiGraph()
        for node in call_graph_data.get("nodes", []):
            self.call_graph.add_node(node.get("id", ""))
        for edge in call_graph_data.get("edges", []):
            self.call_graph.add_edge(edge["source"], edge["target"])

    def analyze_file_impact(self, file_path: str, parsed_files: list[dict], modules: list[dict] | None = None) -> dict:
        """Analyze what would break if a file is changed or removed."""
        if not self.file_graph:
            return {"error": "Graphs not initialized"}

        # Direct dependents (files that import this file)
        direct = list(self.file_graph.predecessors(file_path)) if self.file_graph.has_node(file_path) else []

        # Indirect dependents (transitive)
        indirect = set()
        if self.file_graph.has_node(file_path):
            for d in direct:
                indirect.update(nx.ancestors(self.file_graph, d))
            indirect.discard(file_path)
            indirect -= set(direct)

        # Determine importance
        dep_count = len(direct) + len(indirect)
        if dep_count > 10:
            importance = "critical"
            risk = "critical"
        elif dep_count > 5:
            importance = "critical"
            risk = "high"
        elif dep_count > 2:
            importance = "important"
            risk = "medium"
        elif dep_count > 0:
            importance = "important"
            risk = "low"
        else:
            importance = "optional"
            risk = "low"

        # Find affected modules
        affected_modules = set()
        if modules:
            all_affected_files = set(direct) | indirect
            for mod in modules:
                mod_folders = mod.get("folders", [])
                for af in all_affected_files:
                    for folder in mod_folders:
                        if af.startswith(folder):
                            affected_modules.add(mod.get("module", folder))

        # Breaking changes
        breaking = []
        pf_data = next((pf for pf in parsed_files if pf["file_path"] == file_path), None)
        if pf_data:
            exported_funcs = [f["name"] for f in pf_data["functions"]]
            if exported_funcs:
                breaking.append(f"Functions exposed: {', '.join(exported_funcs[:10])}")
            if pf_data.get("classes"):
                class_names = [c["name"] for c in pf_data["classes"]]
                breaking.append(f"Classes defined: {', '.join(class_names[:10])}")

        # Suggestions
        suggestions = []
        if risk in ("high", "critical"):
            suggestions.append("Add comprehensive tests before modifying")
            suggestions.append("Consider a phased rollout")
        if len(direct) > 5:
            suggestions.append("High fan-in — consider adding an interface/abstraction layer")
        if importance == "optional":
            suggestions.append("Safe to modify — no detected dependents")

        return {
            "target": file_path,
            "target_type": "file",
            "importance": importance,
            "risk_level": risk,
            "direct_dependents": direct,
            "indirect_dependents": list(indirect),
            "affected_modules": list(affected_modules),
            "breaking_changes": breaking,
            "suggestions": suggestions,
            "summary": f"{'Critical' if risk in ('critical', 'high') else 'Moderate' if risk == 'medium' else 'Low'} impact: {len(direct)} direct, {len(indirect)} indirect dependents",
        }

    def analyze_function_impact(self, qualified_name: str, call_graph_data: dict) -> dict:
        """Analyze what would break if a function is changed."""
        if not self.call_graph:
            return {"error": "Call graph not initialized"}

        if not self.call_graph.has_node(qualified_name):
            return {
                "target": qualified_name,
                "target_type": "function",
                "importance": "unknown",
                "risk_level": "unknown",
                "direct_dependents": [],
                "indirect_dependents": [],
                "summary": "Function not found in call graph",
            }

        direct = list(self.call_graph.predecessors(qualified_name))
        indirect = set()
        for d in direct:
            indirect.update(nx.ancestors(self.call_graph, d))
        indirect.discard(qualified_name)
        indirect -= set(direct)

        dep_count = len(direct) + len(indirect)
        if dep_count > 8:
            importance, risk = "critical", "high"
        elif dep_count > 3:
            importance, risk = "important", "medium"
        elif dep_count > 0:
            importance, risk = "important", "low"
        else:
            importance, risk = "optional", "low"

        # Callee impact (what this function calls)
        callees = list(self.call_graph.successors(qualified_name))

        return {
            "target": qualified_name,
            "target_type": "function",
            "importance": importance,
            "risk_level": risk,
            "direct_dependents": [self._short_name(d) for d in direct],
            "indirect_dependents": [self._short_name(d) for d in list(indirect)[:20]],
            "calls": [self._short_name(c) for c in callees],
            "affected_modules": [],
            "breaking_changes": [],
            "suggestions": [],
            "summary": f"{len(direct)} direct callers, {len(indirect)} indirect",
        }

    def _short_name(self, qualified: str) -> str:
        """Shorten qualified name for readability."""
        if "::" in qualified:
            parts = qualified.split("::")
            return f"{Path(parts[0]).name}::{parts[1]}"
        return qualified
