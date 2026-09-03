from __future__ import annotations

import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "RELEASE": 3}


@dataclass(frozen=True)
class ExecutionProvider:
    id: str
    isolation: str
    distributed: bool
    requires: tuple[str, ...]
    max_risk: str
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


PROVIDERS: tuple[ExecutionProvider, ...] = (
    ExecutionProvider("worktree", "process/worktree", False, ("git",), "MEDIUM", "Fast local path; not a security sandbox."),
    ExecutionProvider("docker", "container", False, ("docker",), "RELEASE", "Default isolation target when Docker is healthy."),
    ExecutionProvider("openhands", "provider-defined", False, (), "HIGH", "Optional agent runtime provider; isolation must be reported, never assumed."),
    ExecutionProvider("antigravity", "process/workspace-sandbox", False, ("agy",), "MEDIUM", "Antigravity headless native-agent path; workspace sandbox is not credited as HIGH/RELEASE security isolation."),
    ExecutionProvider("remote", "remote-ephemeral", True, (), "RELEASE", "Provider contract for remote ephemeral workers."),
    ExecutionProvider("kubernetes", "container/cluster", True, ("kubectl",), "RELEASE", "Optional distributed pool; cluster policy remains external."),
    ExecutionProvider("github-runner", "ci-ephemeral", True, ("git",), "RELEASE", "Controlled CI execution for verification/release actions."),
)

PROVIDER_MAP = {p.id: p for p in PROVIDERS}


def provider_availability(provider: ExecutionProvider) -> dict[str, Any]:
    missing = [tool for tool in provider.requires if shutil.which(tool) is None]
    return {"available": not missing, "missing": missing, **provider.to_dict()}


def choose_provider(risk: str, *, preferred: str | None = None, docker_healthy: bool | None = None) -> dict[str, Any]:
    risk = risk.upper()
    if risk not in RISK_ORDER:
        raise ValueError(f"unsupported risk: {risk}")
    if preferred:
        p = PROVIDER_MAP.get(preferred)
        if not p:
            raise ValueError(f"unknown provider: {preferred}")
        if RISK_ORDER[risk] > RISK_ORDER[p.max_risk]:
            return {"status": "blocked", "reason": f"{preferred} isolation is insufficient for {risk}", "provider": p.to_dict()}
        return {"status": "pass", "provider": p.to_dict(), "availability": provider_availability(p)}
    if risk in {"HIGH", "RELEASE"}:
        if docker_healthy is True:
            p = PROVIDER_MAP["docker"]
        else:
            p = PROVIDER_MAP["github-runner"] if risk == "RELEASE" else PROVIDER_MAP["remote"]
    elif risk == "MEDIUM":
        p = PROVIDER_MAP["docker"] if docker_healthy is True else PROVIDER_MAP["worktree"]
    else:
        p = PROVIDER_MAP["worktree"]
    return {"status": "pass", "provider": p.to_dict(), "availability": provider_availability(p)}


PRIVILEGED_ACTIONS = {
    "merge-main": "HIGH",
    "deploy-production": "RELEASE",
    "database-destructive-migration": "RELEASE",
    "delete-cloud-resource": "RELEASE",
    "rotate-production-secret": "RELEASE",
    "publish-store-release": "RELEASE",
}


def authorize_side_effect(action: str, *, risk: str, human_approved: bool = False, proof_status: str | None = None) -> dict[str, Any]:
    required = PRIVILEGED_ACTIONS.get(action)
    if not required:
        return {"status": "pass", "action": action, "privileged": False}
    if RISK_ORDER.get(risk.upper(), -1) < RISK_ORDER[required]:
        return {"status": "blocked", "action": action, "reason": f"action requires {required} risk classification"}
    if not human_approved:
        return {"status": "blocked", "action": action, "reason": "explicit human approval required"}
    if action in {"merge-main", "deploy-production", "database-destructive-migration", "publish-store-release"} and proof_status != "PASS":
        return {"status": "blocked", "action": action, "reason": "valid PASS proof required"}
    return {"status": "pass", "action": action, "privileged": True, "human_approved": True}


def network_policy_for(risk: str, registries: list[str] | None = None) -> dict[str, Any]:
    risk = risk.upper()
    registries = registries or ["pub.dev", "registry.npmjs.org", "pypi.org", "github.com"]
    if risk == "LOW":
        return {"mode": "developer-default", "allow": registries, "deny_unknown": False}
    return {"mode": "allowlist", "allow": registries, "deny_unknown": True}


def secret_broker_policy(environment: str) -> dict[str, Any]:
    environment = environment.lower()
    ttl = 300 if environment == "production" else 900
    return {
        "schema": "nakeuri/secret-broker-policy/v1",
        "environment": environment,
        "raw_secret_to_model": False,
        "write_secret_to_repo": False,
        "log_secret": False,
        "credential_style": "short-lived-scoped",
        "max_ttl_seconds": ttl,
        "production_requires_human_approval": environment == "production",
    }


def fabric_status(root: Path) -> dict[str, Any]:
    root = root.resolve()
    docker = shutil.which("docker") is not None
    return {
        "schema": "nakeuri/execution-fabric/v1",
        "root": str(root),
        "providers": [provider_availability(p) for p in PROVIDERS],
        "risk_routes": {r: choose_provider(r, docker_healthy=docker) for r in RISK_ORDER},
        "side_effect_firewall": sorted(PRIVILEGED_ACTIONS),
        "production_secret_policy": secret_broker_policy("production"),
    }


def container_execution_plan(
    *,
    risk: str,
    image: str,
    workspace: str,
    command: list[str],
    network_required: bool = False,
    workspace_read_only: bool = False,
) -> dict[str, Any]:
    """Return the deterministic hardened Docker invocation for a task.

    The plan contains no secret values. HIGH/RELEASE images must be immutable
    digest references; runtime evidence is validated separately after execution.
    """
    from .runtime_security import docker_run_args, hardened_container_policy

    policy = hardened_container_policy(
        risk, image, network_required=network_required, workspace_read_only=workspace_read_only
    )
    return {
        "status": "pass",
        "schema": "nakeuri/container-execution-plan/v1",
        "policy": policy.to_dict(),
        "argv": docker_run_args(policy, workspace, command),
        "secrets_embedded": False,
    }


def provider_contract(risk: str, provider_id: str) -> dict[str, Any]:
    """Describe proof obligations a runtime provider must satisfy."""
    risk = risk.upper()
    if risk not in RISK_ORDER:
        raise ValueError(f"unsupported risk: {risk}")
    provider = PROVIDER_MAP.get(provider_id)
    if not provider:
        raise ValueError(f"unknown provider: {provider_id}")
    obligations = ["commit_bound_workspace", "structured_execution_result", "usage_telemetry"]
    if risk in {"HIGH", "RELEASE"}:
        obligations += [
            "security_isolation_attestation",
            "network_policy_attestation",
            "resource_limit_attestation",
            "non_root_attestation",
        ]
    if risk == "RELEASE":
        obligations += ["ephemeral_environment", "supply_chain_identity", "human_approval_boundary"]
    return {
        "schema": "nakeuri/runtime-provider-contract/v1",
        "provider": provider.to_dict(),
        "risk": risk,
        "obligations": obligations,
        "provider_claims_are_not_evidence": True,
    }
