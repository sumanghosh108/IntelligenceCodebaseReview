"""Dependency graph builder using NetworkX."""
import networkx as nx
from pathlib import Path


class DependencyGraphBuilder:
    def build_from_parsed(self, parsed_files: list[dict]) -> dict:
        G = nx.DiGraph()

        # Add nodes
        for pf in parsed_files:
            G.add_node(pf["file_path"], language=pf["language"], line_count=pf["line_count"])

        # Build import-to-file mapping
        file_paths = {pf["file_path"] for pf in parsed_files}
        module_map = {}
        for fp in file_paths:
            # Create possible module names from file path
            p = Path(fp)
            stem = p.stem
            parts = list(p.parts)
            # e.g., "backend/core/repo_manager.py" -> "backend.core.repo_manager"
            module_name = ".".join(parts[:-1] + [stem]) if len(parts) > 1 else stem
            module_map[module_name] = fp
            module_map[stem] = fp
            # Also map partial paths
            for i in range(len(parts)):
                partial = ".".join(parts[i:len(parts) - 1] + [stem])
                module_map[partial] = fp

        # Add edges based on imports
        for pf in parsed_files:
            for imp in pf["imports"]:
                # Resolve import to file
                target = self._resolve_import(imp, module_map)
                if target and target != pf["file_path"]:
                    G.add_edge(pf["file_path"], target, type="import")

        # Compute metrics
        nodes_data = []
        for node in G.nodes():
            in_deg = G.in_degree(node)
            out_deg = G.out_degree(node)
            nodes_data.append({
                "file": node,
                "in_degree": in_deg,
                "out_degree": out_deg,
                "total_connections": in_deg + out_deg,
                **G.nodes[node],
            })

        edges_data = [
            {"source": u, "target": v, **d}
            for u, v, d in G.edges(data=True)
        ]

        # Find core modules (highest in-degree)
        core = sorted(nodes_data, key=lambda x: x["in_degree"], reverse=True)[:10]

        # Find isolated modules
        isolated = [n for n in nodes_data if n["total_connections"] == 0]

        # Detect cycles
        cycles = list(nx.simple_cycles(G))
        circular = [list(c) for c in cycles[:20]]  # Limit to 20

        return {
            "nodes": nodes_data,
            "edges": edges_data,
            "core_modules": [c["file"] for c in core if c["in_degree"] > 0],
            "isolated_modules": [i["file"] for i in isolated],
            "circular_dependencies": circular,
            "total_files": len(nodes_data),
            "total_dependencies": len(edges_data),
        }

    def _resolve_import(self, import_str: str, module_map: dict) -> str | None:
        # Direct match
        if import_str in module_map:
            return module_map[import_str]

        # Try parts of the import
        parts = import_str.split(".")
        for i in range(len(parts), 0, -1):
            key = ".".join(parts[:i])
            if key in module_map:
                return module_map[key]

        # Try just the last part
        last = parts[-1]
        if last in module_map:
            return module_map[last]

        return None

    def generate_mermaid(self, graph_data: dict) -> str:
        lines = ["flowchart TD"]
        seen_nodes = set()

        for edge in graph_data["edges"][:50]:  # Limit for readability
            src = edge["source"].replace("/", "_").replace(".", "_").replace("-", "_")
            tgt = edge["target"].replace("/", "_").replace(".", "_").replace("-", "_")
            src_label = Path(edge["source"]).name
            tgt_label = Path(edge["target"]).name

            if src not in seen_nodes:
                lines.append(f"    {src}[{src_label}]")
                seen_nodes.add(src)
            if tgt not in seen_nodes:
                lines.append(f"    {tgt}[{tgt_label}]")
                seen_nodes.add(tgt)

            lines.append(f"    {src} --> {tgt}")

        return "\n".join(lines)
