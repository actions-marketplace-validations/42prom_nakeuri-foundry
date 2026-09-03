from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

CATEGORIES = (
    "greenfield", "feature", "bugfix", "refactor", "security", "performance", "accessibility", "offline",
    "auth", "payments", "database-migration", "api-contract", "ci-cd", "production-incident", "rollback", "native-integration",
    "dependency-upgrade", "architecture", "test-quality", "supply-chain",
)
STACKS = (
    "flutter", "nextjs", "node", "python", "dotnet", "go", "rust", "java",
    "flutter+node", "flutter+nextjs+node", "nextjs+python", "flutter+python", "polyglot-full",
)
RISKS = ("LOW", "MEDIUM", "HIGH", "RELEASE")
FAILURES = ("none", "timeout", "network-loss", "dependency-drift", "schema-drift", "worker-crash", "malicious-input", "rollback-needed")


def _scenario_id(index: int, category: str, stack: str, risk: str, failure: str) -> str:
    digest = hashlib.sha256(f"{index}:{category}:{stack}:{risk}:{failure}".encode()).hexdigest()[:10]
    return f"V3-{index:04d}-{digest.upper()}"


def generate_target_corpus(count: int = 500) -> list[dict[str, Any]]:
    if count < 1:
        raise ValueError("count must be positive")
    rows = []
    for i in range(count):
        category = CATEGORIES[i % len(CATEGORIES)]
        stack = STACKS[(i * 7 + i // len(CATEGORIES)) % len(STACKS)]
        risk = RISKS[(i * 3 + i // len(STACKS)) % len(RISKS)]
        failure = FAILURES[(i * 5 + i // len(RISKS)) % len(FAILURES)]
        rows.append({
            "id": _scenario_id(i + 1, category, stack, risk, failure),
            "category": category,
            "stack": stack,
            "risk": risk,
            "failure_mode": failure,
            "acceptance": {
                "functional": True,
                "no_regression": True,
                "architecture_consistent": True,
                "security_clean": risk in {"HIGH", "RELEASE"} or category in {"security", "auth", "payments", "supply-chain"},
                "proof_required": risk in {"HIGH", "RELEASE"},
                "production_evidence": risk == "RELEASE" or category in {"ci-cd", "production-incident", "rollback"},
            },
            "fairness": {
                "same_repository_snapshot": True,
                "same_task_prompt": True,
                "same_model_policy": True,
                "same_token_budget": True,
                "same_time_budget": True,
                "same_machine_class": True,
                "hidden_tests": True,
            },
        })
    return rows


def write_target_corpus(path: Path, count: int = 500) -> dict[str, Any]:
    rows = generate_target_corpus(count)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(r, sort_keys=True, separators=(",", ":")) for r in rows) + "\n"
    path.write_text(text, encoding="utf-8")
    return {"status": "pass", "path": str(path), "count": len(rows), "sha256": hashlib.sha256(text.encode()).hexdigest()}


def validate_target_corpus(path: Path, minimum: int = 500) -> dict[str, Any]:
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except Exception as exc:
        return {"status": "fail", "reason": f"invalid corpus: {exc}"}
    ids = [r.get("id") for r in rows]
    findings = []
    if len(rows) < minimum:
        findings.append(f"corpus has {len(rows)} tasks; requires >= {minimum}")
    if len(ids) != len(set(ids)):
        findings.append("duplicate scenario IDs")
    present_categories = {r.get("category") for r in rows}
    present_stacks = {r.get("stack") for r in rows}
    present_risks = {r.get("risk") for r in rows}
    if set(CATEGORIES) - present_categories:
        findings.append("missing benchmark categories")
    if set(STACKS) - present_stacks:
        findings.append("missing benchmark stacks")
    if set(RISKS) - present_risks:
        findings.append("missing benchmark risk levels")
    for row in rows:
        fairness = row.get("fairness") or {}
        if not all(fairness.get(k) is True for k in ("same_repository_snapshot", "same_task_prompt", "same_model_policy", "same_token_budget", "same_time_budget", "same_machine_class", "hidden_tests")):
            findings.append(f"{row.get('id')}: incomplete fairness contract")
            break
    return {
        "status": "fail" if findings else "pass",
        "count": len(rows),
        "categories": len(present_categories),
        "stacks": len(present_stacks),
        "risks": sorted(present_risks),
        "findings": findings,
        "rule": "Peer superiority requires identical controlled conditions and hidden acceptance tests; corpus size alone proves nothing.",
    }


def superiority_gate(baseline: dict[str, Any], candidate: dict[str, Any], *, minimum_tasks: int = 300) -> dict[str, Any]:
    """Conservative empirical superiority rule for completed benchmark summaries."""
    findings = []
    if int(candidate.get("count", 0)) < minimum_tasks or int(baseline.get("count", 0)) < minimum_tasks:
        findings.append("insufficient completed tasks")
    if float(candidate.get("acceptance_rate", 0)) <= float(baseline.get("acceptance_rate", 0)):
        findings.append("acceptance rate is not higher")
    if float(candidate.get("first_pass_rate", 0)) < float(baseline.get("first_pass_rate", 0)):
        findings.append("first-pass rate regressed")
    for metric in ("escaped_regressions", "architecture_violations", "duplicate_capabilities", "security_findings"):
        if int(candidate.get(metric, 0)) > int(baseline.get(metric, 0)):
            findings.append(f"{metric} regressed")
    if float(candidate.get("avg_cost", 0)) > float(baseline.get("avg_cost", 0)) * 1.25 and float(candidate.get("acceptance_rate", 0)) < 0.98:
        findings.append("cost increased >25% without near-perfect acceptance")
    return {
        "status": "pass" if not findings else "fail",
        "findings": findings,
        "minimum_tasks": minimum_tasks,
        "rule": "Do not claim peer superiority unless the conservative gate passes on a controlled benchmark.",
    }
