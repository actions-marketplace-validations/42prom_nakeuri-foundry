from __future__ import annotations

from pathlib import Path
from typing import Any

from .scheduler import Scheduler
from .util import ASSET_ROOT, json_load


def budget_policy(risk: str) -> dict[str, Any]:
    risk = risk.lower()
    router = json_load(ASSET_ROOT / "policies" / "model_router.json", {}) or {}
    row = dict(router.get(risk, router.get("medium", {})))
    return {
        "risk": risk.upper(),
        "max_cost_usd": row.get("max_cost_usd"),
        "max_tokens": row.get("max_tokens"),
        "max_agent_seconds": row.get("max_agent_seconds"),
    }


def budget_status(root: Path, task_id: str, risk: str) -> dict[str, Any]:
    usage = Scheduler(root).usage(task_id)
    policy = budget_policy(risk)
    exceeded=[]
    checks=[("cost_usd","max_cost_usd"),("tokens","max_tokens"),("seconds","max_agent_seconds")]
    for used_key,limit_key in checks:
        limit=policy.get(limit_key)
        if limit is not None and usage.get(used_key,0) > limit:
            exceeded.append({"metric":used_key,"used":usage.get(used_key),"limit":limit})
    return {"status":"blocked" if exceeded else "pass","task_id":task_id,"risk":risk.upper(),"policy":policy,"usage":usage,"exceeded":exceeded,"rule":"Budget overruns block further autonomous agent work; a human may change the project policy or task scope explicitly."}
