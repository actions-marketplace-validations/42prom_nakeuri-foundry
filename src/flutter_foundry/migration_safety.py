from __future__ import annotations

from typing import Any

HIGH_RISK_OPS={"drop_table","drop_column","alter_type","rename_column","set_not_null","rewrite_table"}


def assess_migration(migration: dict[str, Any], consumers: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    consumers=consumers or []
    ops=migration.get("operations",[]); findings=[]
    high=[op for op in ops if op.get("op") in HIGH_RISK_OPS]
    if high and not migration.get("backup_verified"):
        findings.append({"severity":"high","issue":"high-risk migration requires verified backup"})
    if high and not migration.get("rollback_tested"):
        findings.append({"severity":"high","issue":"high-risk migration requires tested rollback or forward-fix plan"})
    if migration.get("backward_compatible") is False and not migration.get("expand_contract"):
        findings.append({"severity":"high","issue":"breaking migration requires expand/contract plan"})
    removed={str(op.get("field")) for op in ops if op.get("op") in {"drop_column","rename_column"} and op.get("field")}
    for c in consumers:
        used=set(map(str,c.get("fields",[])))
        hit=sorted(removed & used)
        if hit:
            findings.append({"severity":"high","issue":"deployed consumer still references changed field","consumer":c.get("id"),"fields":hit})
    return {
        "status":"fail" if any(f["severity"]=="high" for f in findings) else "pass",
        "risk":"high" if high else "low",
        "findings":findings,
        "operations":len(ops),
    }
