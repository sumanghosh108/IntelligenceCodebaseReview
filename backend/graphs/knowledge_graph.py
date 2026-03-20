"""Code Knowledge Graph — unified graph of all code relationships.

Combines:
- File dependencies (imports)
- Function call graph
- Class hierarchy (inheritance)
- Data flow (function params → return values)
- Module relationships

Enables:
- "What depends on this function?"
- "Trace execution path from A to B"
- "Impact analysis for any node"
- "Find all code paths through a module"
"""
import logging
import networkx as nx
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CodeKnowledgeGraph:
    """Unified code knowledge graph combining all relationships."""

    def __init__(self):
        self.graph = nx.DiGraph()
        self._file_index: dict[str, dict] = {}
        self._func_index: dict[str, dict] = {}
        self._class_index: dict[str, dict] = {}
        self._module_index: dict[str, dict] = {}

    def build(self, parsed_files: list[dict], dep_data: dict, call_data: dict) -> dict:
        """Build the unified knowledge graph from all parsed data."""
        self.graph.clear()
        self._file_index.clear()
        self._func_index.clear()
        self._class_index.clear()
        self._module_index.clear()

        # 1. Add file nodes
        for pf in parsed_files:
            fp = pf["file_path"]
            node_id = f"file::{fp}"
            self.graph.add_node(node_id, **{
                "type": "file",
                "path": fp,
                "language": pf["language"],
                "line_count": pf["line_count"],
                "size_bytes": pf["size_bytes"],
                "function_count": len(pf["functions"]),
                "class_count": len(pf.get("classes", [])),
            })
            self._file_index[fp] = {"node_id": node_id, "data": pf}

        # 2. Add function nodes
        for pf in parsed_files:
            for func in pf["functions"]:
                func_id = f"func::{pf['file_path']}::{func['name']}"
                self.graph.add_node(func_id, **{
                    "type": "function",
                    "name": func["name"],
                    "file": pf["file_path"],
                    "start_line": func["start_line"],
                    "end_line": func["end_line"],
                    "params": func.get("parameters", []),
                    "lines": func["end_line"] - func["start_line"] + 1,
                })
                self._func_index[func_id] = func

                # Edge: function belongs_to file
                file_node = f"file::{pf['file_path']}"
                self.graph.add_edge(func_id, file_node, type="belongs_to")

        # 3. Add class nodes (Python)
        for pf in parsed_files:
            for cls in pf.get("classes", []):
                cls_id = f"class::{pf['file_path']}::{cls['name']}"
                self.graph.add_node(cls_id, **{
                    "type": "class",
                    "name": cls["name"],
                    "file": pf["file_path"],
                    "methods": cls.get("methods", []),
                    "bases": cls.get("bases", []),
                    "start_line": cls.get("start_line", 0),
                    "end_line": cls.get("end_line", 0),
                })
                self._class_index[cls_id] = cls

                # Edge: class belongs_to file
                file_node = f"file::{pf['file_path']}"
                self.graph.add_edge(cls_id, file_node, type="belongs_to")

                # Edge: class inherits base class
                for base in cls.get("bases", []):
                    base_id = self._find_class(base, parsed_files)
                    if base_id:
                        self.graph.add_edge(cls_id, base_id, type="inherits")

        # 4. File dependency edges (imports)
        for edge in dep_data.get("edges", []):
            src = f"file::{edge['source']}"
            tgt = f"file::{edge['target']}"
            if self.graph.has_node(src) and self.graph.has_node(tgt):
                self.graph.add_edge(src, tgt, type="imports")

        # 5. Function call edges
        for edge in call_data.get("edges", []):
            src = f"func::{edge['source']}"
            tgt = f"func::{edge['target']}"
            if self.graph.has_node(src) and self.graph.has_node(tgt):
                self.graph.add_edge(src, tgt, type="calls")

        # 6. Infer data flow
        self._build_data_flow(parsed_files)

        # 7. Detect modules
        self._detect_modules(parsed_files)

        logger.info(
            f"Knowledge graph: {self.graph.number_of_nodes()} nodes, "
            f"{self.graph.number_of_edges()} edges"
        )

        return self.get_summary()

    def _find_class(self, class_name: str, parsed_files: list[dict]) -> Optional[str]:
        for pf in parsed_files:
            for cls in pf.get("classes", []):
                if cls["name"] == class_name:
                    return f"class::{pf['file_path']}::{cls['name']}"
        return None

    def _build_data_flow(self, parsed_files: list[dict]):
        """Infer data flow edges from shared parameter/return patterns."""
        producers: dict[str, list[str]] = {}
        consumers: dict[str, list[str]] = {}

        for pf in parsed_files:
            for func in pf["functions"]:
                func_id = f"func::{pf['file_path']}::{func['name']}"
                for param in func.get("parameters", []):
                    clean = param.split(":")[0].split("=")[0].strip()
                    if clean and clean not in ("self", "cls", "args", "kwargs"):
                        consumers.setdefault(clean, []).append(func_id)
                producers.setdefault(func["name"], []).append(func_id)

        for param_name, consumer_funcs in consumers.items():
            if param_name in producers:
                for producer in producers[param_name]:
                    for consumer in consumer_funcs:
                        if producer != consumer and not self.graph.has_edge(producer, consumer):
                            self.graph.add_edge(producer, consumer, type="data_flow")

    def _detect_modules(self, parsed_files: list[dict]):
        modules: dict[str, list[str]] = {}
        for pf in parsed_files:
            parts = Path(pf["file_path"]).parts
            module_name = parts[0] if len(parts) > 1 else "root"
            modules.setdefault(module_name, []).append(pf["file_path"])

        for mod_name, files in modules.items():
            mod_id = f"module::{mod_name}"
            total_lines = sum(
                self.graph.nodes[f"file::{fp}"].get("line_count", 0)
                for fp in files if self.graph.has_node(f"file::{fp}")
            )
            self.graph.add_node(mod_id, **{
                "type": "module",
                "name": mod_name,
                "file_count": len(files),
                "total_lines": total_lines,
            })
            self._module_index[mod_name] = {"files": files}

            for fp in files:
                file_node = f"file::{fp}"
                if self.graph.has_node(file_node):
                    self.graph.add_edge(file_node, mod_id, type="belongs_to")

    # ==================== QUERY METHODS ====================

    def get_summary(self) -> dict:
        type_counts = {}
        for _, data in self.graph.nodes(data=True):
            t = data.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        edge_type_counts = {}
        for _, _, data in self.graph.edges(data=True):
            t = data.get("type", "unknown")
            edge_type_counts[t] = edge_type_counts.get(t, 0) + 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": type_counts,
            "edge_types": edge_type_counts,
            "modules": list(self._module_index.keys()),
        }

    def get_node_neighbors(self, node_id: str) -> dict:
        if not self.graph.has_node(node_id):
            return {"error": f"Node {node_id} not found"}

        incoming = []
        for pred in self.graph.predecessors(node_id):
            edge = self.graph.edges[pred, node_id]
            incoming.append({"from": pred, "type": edge.get("type", "unknown")})

        outgoing = []
        for succ in self.graph.successors(node_id):
            edge = self.graph.edges[node_id, succ]
            outgoing.append({"to": succ, "type": edge.get("type", "unknown")})

        return {
            "node": node_id,
            "data": dict(self.graph.nodes[node_id]),
            "incoming": incoming,
            "outgoing": outgoing,
            "in_degree": self.graph.in_degree(node_id),
            "out_degree": self.graph.out_degree(node_id),
        }

    def trace_path(self, source: str, target: str) -> dict:
        """Find all paths between two nodes."""
        if not self.graph.has_node(source) or not self.graph.has_node(target):
            return {"error": "Source or target not found", "paths": []}

        try:
            shortest = nx.shortest_path(self.graph, source, target)
            all_paths = list(nx.all_simple_paths(self.graph, source, target, cutoff=8))[:10]

            path_details = []
            for path in all_paths:
                edges = []
                for i in range(len(path) - 1):
                    edge_data = self.graph.edges[path[i], path[i + 1]]
                    edges.append({
                        "from": path[i],
                        "to": path[i + 1],
                        "type": edge_data.get("type", "unknown"),
                    })
                path_details.append({"nodes": path, "edges": edges, "length": len(path)})

            return {
                "source": source,
                "target": target,
                "shortest_path": shortest,
                "all_paths": path_details,
                "total_paths": len(all_paths),
            }
        except nx.NetworkXNoPath:
            return {"source": source, "target": target, "paths": [], "error": "No path exists"}
        except Exception as e:
            return {"error": str(e), "paths": []}

    def get_dependents(self, node_id: str, depth: int = 3) -> dict:
        """Find everything that depends on a node (reverse traversal)."""
        if not self.graph.has_node(node_id):
            return {"error": f"Node {node_id} not found"}

        dependents = {"direct": [], "indirect": [], "by_type": {}}
        visited = set()
        queue = [(node_id, 0)]

        while queue:
            current, level = queue.pop(0)
            if current in visited or level > depth:
                continue
            visited.add(current)

            for pred in self.graph.predecessors(current):
                if pred not in visited:
                    edge = self.graph.edges[pred, current]
                    edge_type = edge.get("type", "unknown")
                    entry = {"node": pred, "via": edge_type, "depth": level + 1}

                    if level == 0:
                        dependents["direct"].append(entry)
                    else:
                        dependents["indirect"].append(entry)

                    dependents["by_type"].setdefault(edge_type, []).append(pred)
                    queue.append((pred, level + 1))

        return {
            "target": node_id,
            "direct_count": len(dependents["direct"]),
            "indirect_count": len(dependents["indirect"]),
            **dependents,
        }

    def get_hotspots(self, top_n: int = 15) -> dict:
        """Find the most connected/critical nodes."""
        try:
            pagerank = nx.pagerank(self.graph, alpha=0.85)
        except Exception:
            pagerank = {n: 0 for n in self.graph.nodes()}

        try:
            betweenness = nx.betweenness_centrality(self.graph)
        except Exception:
            betweenness = {n: 0 for n in self.graph.nodes()}

        hotspots = []
        for node in self.graph.nodes():
            data = self.graph.nodes[node]
            hotspots.append({
                "node": node,
                "type": data.get("type", "unknown"),
                "name": data.get("name", data.get("path", node)),
                "pagerank": round(pagerank.get(node, 0), 6),
                "betweenness": round(betweenness.get(node, 0), 6),
                "in_degree": self.graph.in_degree(node),
                "out_degree": self.graph.out_degree(node),
                "score": round(
                    pagerank.get(node, 0) * 1000 +
                    betweenness.get(node, 0) * 500 +
                    self.graph.in_degree(node) * 2,
                    2,
                ),
            })

        hotspots.sort(key=lambda x: x["score"], reverse=True)

        return {
            "hotspots": hotspots[:top_n],
            "bottlenecks": sorted(hotspots, key=lambda x: x["betweenness"], reverse=True)[:top_n],
            "most_depended": sorted(hotspots, key=lambda x: x["in_degree"], reverse=True)[:top_n],
        }

    def get_module_interactions(self) -> dict:
        interactions = {}
        for u, v, data in self.graph.edges(data=True):
            u_data = self.graph.nodes.get(u, {})
            v_data = self.graph.nodes.get(v, {})

            u_file = u_data.get("file", u_data.get("path", ""))
            v_file = v_data.get("file", v_data.get("path", ""))

            if not u_file or not v_file:
                continue

            u_mod = Path(u_file).parts[0] if len(Path(u_file).parts) > 1 else "root"
            v_mod = Path(v_file).parts[0] if len(Path(v_file).parts) > 1 else "root"

            if u_mod != v_mod:
                key = f"{u_mod} -> {v_mod}"
                if key not in interactions:
                    interactions[key] = {"from": u_mod, "to": v_mod, "count": 0, "types": []}
                interactions[key]["count"] += 1
                edge_type = data.get("type", "unknown")
                if edge_type not in interactions[key]["types"]:
                    interactions[key]["types"].append(edge_type)

        return {
            "interactions": list(interactions.values()),
            "modules": list(self._module_index.keys()),
        }

    def search_nodes(self, query: str, node_type: str = None) -> list[dict]:
        results = []
        query_lower = query.lower()
        for node, data in self.graph.nodes(data=True):
            if node_type and data.get("type") != node_type:
                continue
            name = data.get("name", data.get("path", node)).lower()
            if query_lower in name or query_lower in node.lower():
                results.append({
                    "node_id": node,
                    "type": data.get("type", "unknown"),
                    "name": data.get("name", data.get("path", node)),
                    "in_degree": self.graph.in_degree(node),
                    "out_degree": self.graph.out_degree(node),
                })
        return results[:20]

    def export_for_visualization(self) -> dict:
        nodes = []
        for node, data in self.graph.nodes(data=True):
            nodes.append({
                "id": node,
                "label": data.get("name", data.get("path", node)),
                "type": data.get("type", "unknown"),
                **{k: v for k, v in data.items() if k not in ("type",)},
            })

        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({
                "source": u,
                "target": v,
                "type": data.get("type", "unknown"),
            })

        return {"nodes": nodes, "edges": edges}
