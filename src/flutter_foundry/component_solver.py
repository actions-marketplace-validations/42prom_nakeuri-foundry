from __future__ import annotations

from typing import Any
from .component_registry import ComponentRegistry, ComponentError

RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "RELEASE": 3}


def solve_components(requested: list[str], platforms: list[str] | None = None, max_risk: str = "RELEASE") -> dict[str, Any]:
    platforms = [p.lower() for p in (platforms or [])]
    try:
        resolved = ComponentRegistry().resolve(requested)
    except ComponentError as e:
        return {"status": "fail", "findings": [str(e)], "components": []}
    comps = resolved.get("components", [])
    findings = []
    max_rank = RISK_ORDER.get(max_risk.upper(), 3)
    aggregate_rank = 0
    security_tags = set(); acceptance = []; verification = []
    for comp in comps:
        risk = str(comp.get("risk", "MEDIUM")).upper()
        rank = RISK_ORDER.get(risk, 1); aggregate_rank = max(aggregate_rank, rank)
        if rank > max_rank: findings.append(f"{comp.get('id')} exceeds max risk {max_risk}")
        supported = [str(p).lower() for p in comp.get("platforms", [])]
        if platforms and supported and not any(p in supported for p in platforms):
            findings.append(f"{comp.get('id')} does not support requested platforms {platforms}")
        security_tags.update(comp.get("security_tags", []))
        acceptance.extend(comp.get("acceptance", []))
        verification.extend(comp.get("verification", []))
    risk_name = next((k for k, v in RISK_ORDER.items() if v == aggregate_rank), "MEDIUM")
    return {
        "status": "fail" if findings else "pass",
        "findings": findings,
        "components": comps,
        "aggregate_risk": risk_name,
        "security_tags": sorted(security_tags),
        "acceptance": sorted(set(acceptance)),
        "verification": sorted(set(verification)),
    }
