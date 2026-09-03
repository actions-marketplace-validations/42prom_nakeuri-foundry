from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .platform_adapters import detect_project_surfaces
from .semantic_engine import semantic_project_graph


@dataclass(frozen=True)
class GraphNode:
    id: str
    kind: str
    name: str
    root: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    kind: str

    def to_dict(self) -> dict[str, Any]: return asdict(self)


def _node_id(kind: str, root: str, name: str) -> str:
    digest = hashlib.sha256(f"{kind}:{root}:{name}".encode()).hexdigest()[:12]
    return f"{kind}:{digest}"


def build_project_graph(root: Path) -> dict[str, Any]:
    root = root.resolve()
    surfaces = detect_project_surfaces(root)
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    project_id = _node_id("project", ".", root.name)
    nodes.append(GraphNode(project_id, "project", root.name, ".", {}))
    for surface in surfaces:
        sid = _node_id("surface", surface["root"], surface["id"])
        nodes.append(GraphNode(sid, "surface", surface["id"], surface["root"], {k: v for k, v in surface.items() if k != "root"}))
        edges.append(GraphEdge(project_id, sid, "contains"))
        for manifest in surface.get("manifests", []):
            mid = _node_id("manifest", surface["root"], manifest)
            nodes.append(GraphNode(mid, "manifest", manifest, surface["root"], {}))
            edges.append(GraphEdge(sid, mid, "declares"))
    semantic = semantic_project_graph(root)
    return {
        "schema": "nakeuri/software-knowledge-graph/v2",
        "nodes": [n.to_dict() for n in nodes],
        "edges": [e.to_dict() for e in edges],
        "surface_count": len(surfaces),
        "semantic": semantic,
        "semantic_node_count": len(semantic.get("nodes", [])),
        "semantic_edge_count": len(semantic.get("edges", [])),
        "rule": "Manifest topology and source semantics are separate layers; authoritative analyzers override heuristic fallback when available.",
    }


def write_project_graph(root: Path) -> Path:
    root = root.resolve()
    p = root / ".factory" / "graph" / "software-knowledge-graph.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(build_project_graph(root), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def compare_contract_snapshots(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare normalized cross-language contract snapshots.

    Snapshot schema:
      {"contract_id":"user","provider":"openapi","fields":{"email":{"type":"string","required":true}}}
    Adapters normalize their native schemas before calling this deterministic engine.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for snap in snapshots:
        grouped.setdefault(str(snap.get("contract_id", "")), []).append(snap)
    findings: list[dict[str, Any]] = []
    for contract_id, items in grouped.items():
        if not contract_id or len(items) < 2:
            continue
        all_fields = sorted({f for item in items for f in (item.get("fields") or {})})
        for field in all_fields:
            seen = []
            for item in items:
                spec = (item.get("fields") or {}).get(field)
                seen.append((item.get("provider"), spec))
            present = [spec for _, spec in seen if spec is not None]
            if len(present) != len(seen):
                findings.append({"contract_id": contract_id, "field": field, "severity": "high", "issue": "field presence drift", "providers": seen})
                continue
            signatures = {(str(spec.get("type")), bool(spec.get("required", False)), bool(spec.get("nullable", False))) for spec in present}
            if len(signatures) > 1:
                findings.append({"contract_id": contract_id, "field": field, "severity": "high", "issue": "type/required/nullability drift", "providers": seen})
    return {"status": "fail" if findings else "pass", "contracts": len(grouped), "findings": findings}


def load_contract_snapshots(root: Path) -> list[dict[str, Any]]:
    directory = root.resolve() / ".factory" / "contracts"
    if not directory.exists():
        return []
    out = []
    for p in sorted(directory.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, list): out.extend(x for x in data if isinstance(x, dict))
            elif isinstance(data, dict): out.append(data)
        except Exception:
            out.append({"contract_id": f"invalid:{p.name}", "provider": "invalid", "fields": {}, "_invalid": True})
    return out


def contract_status(root: Path) -> dict[str, Any]:
    snaps = load_contract_snapshots(root)
    invalid = [x for x in snaps if x.get("_invalid")]
    if invalid:
        return {"status": "fail", "findings": [{"issue": "invalid contract snapshot JSON", "contract_id": x["contract_id"]} for x in invalid]}
    result = compare_contract_snapshots(snaps)
    result["snapshot_count"] = len(snaps)
    return result
