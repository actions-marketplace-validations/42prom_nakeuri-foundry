from __future__ import annotations

from typing import Any

REVIEW_SCHEMA = "nakeuri/review-output/v1"
WORKER_SCHEMA = "nakeuri/worker-output/v1"
_MAX_TEXT = 20_000
_MAX_FINDINGS = 100


def _exact_keys(payload: dict[str, Any], allowed: set[str]) -> tuple[bool, str]:
    extra = set(payload) - allowed
    if extra:
        return False, f"unknown fields: {sorted(extra)}"
    return True, "ok"


def validate_review_output(payload: Any) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "review output must be an object"
    ok, why = _exact_keys(payload, {"schema", "status", "findings"})
    if not ok:
        return ok, why
    if payload.get("schema") != REVIEW_SCHEMA:
        return False, "unsupported review output schema"
    if payload.get("status") not in {"PASS", "FAIL", "WARN"}:
        return False, "invalid review status"
    findings = payload.get("findings")
    if not isinstance(findings, list) or len(findings) > _MAX_FINDINGS:
        return False, "findings must be a bounded list"
    for i, finding in enumerate(findings):
        if not isinstance(finding, dict):
            return False, f"finding {i} must be an object"
        ok, why = _exact_keys(finding, {"severity", "message", "evidence"})
        if not ok:
            return False, f"finding {i}: {why}"
        if finding.get("severity") not in {"BLOCKER", "HIGH", "MEDIUM", "LOW"}:
            return False, f"finding {i}: invalid severity"
        for key in ("message", "evidence"):
            value = finding.get(key)
            if not isinstance(value, str) or not value.strip() or len(value) > _MAX_TEXT:
                return False, f"finding {i}: invalid {key}"
    return True, "ok"


def validate_worker_output(payload: Any) -> tuple[bool, str]:
    """Optional strict metadata contract for executors that emit worker JSON.

    Code correctness still comes from the committed diff and deterministic gates; this
    object only carries bounded machine-readable execution metadata.
    """
    if payload is None:
        return True, "no worker metadata"
    if not isinstance(payload, dict):
        return False, "worker output must be an object"
    ok, why = _exact_keys(payload, {"schema", "status", "summary", "tests"})
    if not ok:
        return ok, why
    if payload.get("schema") != WORKER_SCHEMA:
        return False, "unsupported worker output schema"
    if payload.get("status") not in {"COMPLETED", "BLOCKED"}:
        return False, "invalid worker status"
    if not isinstance(payload.get("summary"), str) or len(payload["summary"]) > _MAX_TEXT:
        return False, "invalid worker summary"
    tests = payload.get("tests")
    if not isinstance(tests, list) or len(tests) > 100 or not all(isinstance(x, str) and len(x) <= 1000 for x in tests):
        return False, "invalid worker tests"
    return True, "ok"
