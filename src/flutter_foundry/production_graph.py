from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


ALLOWED_KINDS = {"mobile", "web", "api", "worker", "database", "infra", "service"}


def validate_release_graph(data: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    components = data.get("components", [])
    ids = [str(c.get("id", "")) for c in components]
    if len(ids) != len(set(ids)):
        findings.append("duplicate component id")
    known = set(ids)
    for c in components:
        if not c.get("id"): findings.append("component id missing")
        if c.get("kind") not in ALLOWED_KINDS: findings.append(f"{c.get('id')}: unsupported kind")
        for dep in c.get("depends_on", []):
            if dep not in known: findings.append(f"{c.get('id')}: unknown dependency {dep}")
    order = _topological_order(components)
    if order is None: findings.append("dependency cycle")
    for migration in data.get("migrations", []):
        if migration.get("destructive") and not migration.get("rollback_tested"):
            findings.append(f"migration {migration.get('id')}: destructive change requires tested rollback")
        if migration.get("backward_compatible") is False and not migration.get("expand_contract"):
            findings.append(f"migration {migration.get('id')}: breaking migration requires expand/contract plan")
    return {"status": "fail" if findings else "pass", "findings": findings, "order": order or []}


def _topological_order(components: list[dict[str, Any]]) -> list[str] | None:
    indegree: dict[str, int] = {str(c.get("id")): 0 for c in components}
    graph: dict[str, list[str]] = defaultdict(list)
    for c in components:
        cid = str(c.get("id"))
        for dep in c.get("depends_on", []):
            graph[str(dep)].append(cid); indegree[cid] += 1
    q = deque(sorted(k for k, v in indegree.items() if v == 0)); order = []
    while q:
        n = q.popleft(); order.append(n)
        for child in sorted(graph[n]):
            indegree[child] -= 1
            if indegree[child] == 0: q.append(child)
    return order if len(order) == len(indegree) else None


def init_release_graph(root: Path, force: bool = False) -> Path:
    root = root.resolve(); p = root / ".factory" / "production" / "release-graph.json"
    if p.exists() and not force: return p
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "nakeuri/release-graph/v1",
        "components": [],
        "migrations": [],
        "policy": {"staged_rollout": True, "health_gate": True, "proof_required": True, "human_production_approval": True},
    }
    p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def release_plan(root: Path) -> dict[str, Any]:
    p = root.resolve() / ".factory" / "production" / "release-graph.json"
    if not p.exists(): return {"status": "fail", "reason": "release graph missing", "path": str(p)}
    try: data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc: return {"status": "fail", "reason": f"invalid release graph: {exc}"}
    if data.get("schema") != "nakeuri/release-graph/v1": return {"status": "fail", "reason": "unsupported release graph schema"}
    validation = validate_release_graph(data)
    if validation["status"] != "pass": return validation
    return {
        "status": "pass",
        "deploy_order": validation["order"],
        "rollback_order": list(reversed(validation["order"])),
        "policy": data.get("policy", {}),
        "components": data.get("components", []),
        "migrations": data.get("migrations", []),
    }
