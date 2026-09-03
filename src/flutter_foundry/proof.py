from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .evidence import validate_evidence
from .reviews import validate_review
from .util import json_dump
from .safe_paths import resolve_inside, safe_identifier

STRICT_RISKS = {"HIGH", "RELEASE"}


def _git(root: Path, *args: str) -> str | None:
    try:
        p = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, timeout=5)
        return p.stdout.strip() if p.returncode == 0 else None
    except Exception:
        return None


def _artifact_ok(root: Path, ev: dict[str, Any]) -> tuple[bool, str]:
    art = ev.get("artifact")
    if not art:
        return True, "no artifact"
    try:
        path = resolve_inside(root, str(art.get("path", "")), must_exist=True)
    except ValueError as exc:
        return False, f"unsafe artifact path: {exc}"
    if not path.is_file(): return False, "artifact is not a file"
    expected = art.get("sha256")
    if expected:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected: return False, "artifact hash mismatch"
    if art.get("size") is not None and path.stat().st_size != art.get("size"):
        return False, "artifact size mismatch"
    return True, "ok"


def build_proof(
    root: Path,
    task_id: str,
    task: str,
    risk: dict[str, Any],
    verification: dict[str, Any],
    requirements: list[str] | None = None,
    changed_files: list[str] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    reviews: list[dict[str, Any]] | None = None,
    writer: str | None = None,
) -> dict[str, Any]:
    root = root.resolve(); evidence = evidence or []; reviews = reviews or []
    commit = _git(root, "rev-parse", "HEAD")
    invalid_evidence = []
    for ev in evidence:
        ok, why = validate_evidence(ev)
        if ok: ok, why = _artifact_ok(root, ev)
        if not ok: invalid_evidence.append({"kind": ev.get("kind"), "reason": why})
    invalid_reviews = []
    for review in reviews:
        ok, why = validate_review(root, review, expected_commit=commit)
        if not ok: invalid_reviews.append({"reviewer": review.get("reviewer"), "reason": why})
    risk_level = str(risk.get("level", risk.get("risk", "MEDIUM"))).upper()
    verification_status = str(verification.get("status", "fail")).lower()
    strict = risk_level in STRICT_RISKS
    verification_ok = verification_status == "pass" if strict else verification_status in {"pass", "pass_with_gaps"}
    blockers = verification.get("blocking", [])
    review_blockers = [r for r in reviews if r.get("status") == "FAIL"]
    has_independent_pass = any(r.get("status") == "PASS" and r.get("reviewer") != (writer or r.get("writer")) for r in reviews)
    review_required = strict
    result = "PASS" if (
        commit and verification_ok and not blockers and not invalid_evidence and not invalid_reviews and not review_blockers and (has_independent_pass or not review_required)
    ) else "FAIL"
    return {
        "schema": "nakeuri-flutter-foundry/proof/v3",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "task": task,
        "requirements": requirements or [],
        "git": {"commit": commit, "branch": _git(root, "branch", "--show-current")},
        "changed_files": changed_files or [],
        "risk": risk,
        "verification": verification,
        "evidence": evidence,
        "reviews": reviews,
        "writer": writer,
        "invalid_evidence": invalid_evidence,
        "invalid_reviews": invalid_reviews,
        "strict_risk": strict,
        "result": result,
    }


def write_proof(root: Path, proof: dict[str, Any]) -> Path:
    safe = safe_identifier(str(proof.get("task_id", "task")), label="task_id")
    p = root / ".factory" / "proofs" / f"{safe}.json"
    json_dump(p, proof)
    return p


def validate_proof(root: Path, proof: dict[str, Any], require_clean_commit: bool = True) -> dict[str, Any]:
    root = root.resolve(); findings = []
    if proof.get("schema") != "nakeuri-flutter-foundry/proof/v3": findings.append("unsupported proof schema")
    if proof.get("result") != "PASS": findings.append("proof result is not PASS")
    current = _git(root, "rev-parse", "HEAD"); bound = proof.get("git", {}).get("commit")
    if require_clean_commit and current and bound != current: findings.append("proof is not bound to current HEAD")
    risk_level = str(proof.get("risk", {}).get("level", proof.get("risk", {}).get("risk", "MEDIUM"))).upper()
    verification_status = str(proof.get("verification", {}).get("status", "fail")).lower()
    if risk_level in STRICT_RISKS and verification_status != "pass": findings.append("HIGH/RELEASE proof requires verification status PASS")
    if proof.get("verification", {}).get("blocking"): findings.append("verification has blocking failures")
    for ev in proof.get("evidence", []):
        ok, why = validate_evidence(ev)
        if ok: ok, why = _artifact_ok(root, ev)
        if not ok: findings.append(f"invalid evidence {ev.get('kind')}: {why}")
    valid_pass_reviews = 0
    for review in proof.get("reviews", []):
        ok, why = validate_review(root, review, expected_commit=bound)
        if not ok: findings.append(f"invalid review {review.get('reviewer')}: {why}")
        elif review.get("status") == "FAIL": findings.append(f"blocking review by {review.get('reviewer')}")
        elif review.get("status") == "PASS": valid_pass_reviews += 1
    if risk_level in STRICT_RISKS and valid_pass_reviews < 1: findings.append("HIGH/RELEASE proof requires an independent PASS review")
    return {"status": "fail" if findings else "pass", "findings": findings}
