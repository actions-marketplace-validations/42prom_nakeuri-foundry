from __future__ import annotations

from pathlib import Path
from typing import Any
from .proof import validate_proof
from .reviews import validate_review


def merge_decision(root: Path, proof: dict[str, Any], reviews: list[dict[str, Any]], human_approved: bool = False) -> dict[str, Any]:
    proof_check = validate_proof(root, proof)
    findings = list(proof_check.get("findings", []))
    commit = proof.get("git", {}).get("commit")
    for r in reviews:
        ok, why = validate_review(root, r, expected_commit=commit)
        if not ok: findings.append(f"invalid review: {why}")
        elif r.get("status") == "FAIL": findings.append(f"blocking review: {r.get('reviewer')}")
    risk = str(proof.get("risk", {}).get("level", proof.get("risk", {}).get("risk", "MEDIUM"))).upper()
    if risk in {"HIGH", "RELEASE"} and not human_approved:
        findings.append("HIGH/RELEASE merge requires human approval")
    return {"status": "blocked" if findings else "mergeable", "findings": findings, "commit": commit, "risk": risk}
