from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import RiskResult
from .util import ASSET_ROOT, json_load


def classify_risk(task: str, changed_files: int = 0, call_sites: int = 0, component_risks: list[str] | None = None) -> RiskResult:
    cfg = json_load(ASSET_ROOT / "policies" / "risk.json", {})
    router = json_load(ASSET_ROOT / "policies" / "model_router.json", {})
    text = task.lower()
    score = 0
    reasons: list[str] = []

    high_hits = [kw for kw in cfg.get("high_keywords", []) if kw in text]
    medium_hits = [kw for kw in cfg.get("medium_keywords", []) if kw in text]
    if high_hits:
        score += min(8, 4 + len(high_hits))
        reasons.append("high-risk domain: " + ", ".join(high_hits[:5]))
    if medium_hits:
        score += min(4, len(medium_hits))
        reasons.append("cross-cutting domain: " + ", ".join(medium_hits[:5]))

    if changed_files > cfg.get("files", {}).get("medium_max", 5):
        score += 4
        reasons.append(f"large file blast radius ({changed_files} files)")
    elif changed_files > cfg.get("files", {}).get("low_max", 2):
        score += 2
        reasons.append(f"multi-file change ({changed_files} files)")

    safe = cfg.get("call_sites", {}).get("safe_max", 3)
    caution = cfg.get("call_sites", {}).get("caution_max", 10)
    if call_sites > caution:
        score += 5
        reasons.append(f"wide symbol blast radius ({call_sites} call sites)")
    elif call_sites > safe:
        score += 2
        reasons.append(f"non-trivial symbol blast radius ({call_sites} call sites)")

    component_risks = component_risks or []
    if "high" in component_risks:
        score += 4
        reasons.append("selected component has high risk")
    elif "medium" in component_risks:
        score += 1
        reasons.append("selected component has medium risk")

    t = cfg.get("thresholds", {})
    if score >= t.get("release_score", 12):
        level = "release"
    elif score >= t.get("high_score", 7):
        level = "high"
    elif score >= t.get("medium_score", 3):
        level = "medium"
    else:
        level = "low"

    return RiskResult(level=level, score=score, reasons=reasons or ["no elevated risk signal"], execution=router.get(level, router.get("medium", {})))
