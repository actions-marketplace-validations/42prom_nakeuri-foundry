from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .execution_fabric import RISK_ORDER

_DIGEST_RE = re.compile(r"^[A-Za-z0-9._/-]+@sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class HardenedContainerPolicy:
    risk: str
    image: str
    user: str = "65532:65532"
    read_only_rootfs: bool = True
    no_new_privileges: bool = True
    cap_drop_all: bool = True
    pids_limit: int = 512
    memory_mb: int = 4096
    cpus: float = 2.0
    tmpfs_mb: int = 512
    network_mode: str = "none"
    workspace_read_only: bool = False
    seccomp_profile: str = "runtime/default"
    apparmor_profile: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def image_is_digest_pinned(image: str) -> bool:
    return bool(_DIGEST_RE.fullmatch(image.strip()))


def hardened_container_policy(
    risk: str,
    image: str,
    *,
    network_required: bool = False,
    workspace_read_only: bool = False,
) -> HardenedContainerPolicy:
    risk = risk.upper()
    if risk not in RISK_ORDER:
        raise ValueError(f"unsupported risk: {risk}")
    if risk in {"HIGH", "RELEASE"} and not image_is_digest_pinned(image):
        raise ValueError("HIGH/RELEASE container images must be pinned by sha256 digest")
    network_mode = "foundry-egress" if network_required else "none"
    if risk == "LOW":
        return HardenedContainerPolicy(
            risk=risk,
            image=image,
            user="65532:65532",
            memory_mb=2048,
            cpus=2.0,
            network_mode="bridge" if network_required else "none",
            workspace_read_only=workspace_read_only,
        )
    if risk == "MEDIUM":
        return HardenedContainerPolicy(
            risk=risk,
            image=image,
            memory_mb=4096,
            cpus=2.0,
            network_mode=network_mode,
            workspace_read_only=workspace_read_only,
        )
    return HardenedContainerPolicy(
        risk=risk,
        image=image,
        memory_mb=6144 if risk == "HIGH" else 8192,
        cpus=2.0 if risk == "HIGH" else 4.0,
        pids_limit=384,
        network_mode=network_mode,
        workspace_read_only=workspace_read_only,
    )


def docker_run_args(policy: HardenedContainerPolicy, workspace: str, command: list[str]) -> list[str]:
    """Build a hardened docker CLI invocation without ever embedding secrets."""
    if not workspace:
        raise ValueError("workspace required")
    args = ["docker", "run", "--rm", "--init", "--user", policy.user]
    if policy.read_only_rootfs:
        args += ["--read-only"]
    if policy.no_new_privileges:
        args += ["--security-opt", "no-new-privileges:true"]
    if policy.cap_drop_all:
        args += ["--cap-drop", "ALL"]
    args += [
        "--pids-limit", str(policy.pids_limit),
        "--memory", f"{policy.memory_mb}m",
        "--cpus", str(policy.cpus),
        "--tmpfs", f"/tmp:rw,nosuid,nodev,noexec,size={policy.tmpfs_mb}m",
        "--network", policy.network_mode,
        "--security-opt", f"seccomp={policy.seccomp_profile}",
    ]
    if policy.apparmor_profile:
        args += ["--security-opt", f"apparmor={policy.apparmor_profile}"]
    mount_mode = "ro" if policy.workspace_read_only else "rw"
    args += ["--mount", f"type=bind,src={workspace},dst=/workspace,{mount_mode}", "--workdir", "/workspace"]
    args += [policy.image]
    args += list(command)
    return args


def validate_runtime_attestation(attestation: dict[str, Any], risk: str) -> dict[str, Any]:
    """Validate observed runtime facts, not requested policy.

    HIGH/RELEASE proof must bind to a digest-pinned image and demonstrate the
    actual runtime had a non-root user, read-only rootfs, dropped capabilities,
    no-new-privileges, bounded resources, and controlled networking.
    """
    risk = risk.upper()
    findings: list[dict[str, str]] = []
    required = {
        "image": attestation.get("image"),
        "user": attestation.get("user"),
        "read_only_rootfs": attestation.get("read_only_rootfs"),
        "cap_drop_all": attestation.get("cap_drop_all"),
        "no_new_privileges": attestation.get("no_new_privileges"),
        "network_mode": attestation.get("network_mode"),
        "memory_mb": attestation.get("memory_mb"),
        "cpus": attestation.get("cpus"),
    }
    if risk in {"HIGH", "RELEASE"} and not image_is_digest_pinned(str(required["image"] or "")):
        findings.append({"severity": "blocker", "issue": "runtime image is not digest pinned"})
    if str(required["user"] or "").split(":", 1)[0] in {"", "0", "root"}:
        findings.append({"severity": "blocker", "issue": "runtime executed as root"})
    for key in ("read_only_rootfs", "cap_drop_all", "no_new_privileges"):
        if required[key] is not True:
            findings.append({"severity": "blocker" if risk in {"HIGH", "RELEASE"} else "high", "issue": f"{key} not proven"})
    if risk in {"HIGH", "RELEASE"} and str(required["network_mode"] or "") not in {"none", "foundry-egress"}:
        findings.append({"severity": "blocker", "issue": "network egress is not constrained"})
    try:
        if int(required["memory_mb"] or 0) <= 0 or float(required["cpus"] or 0) <= 0:
            findings.append({"severity": "high", "issue": "resource limits not proven"})
    except Exception:
        findings.append({"severity": "high", "issue": "invalid resource-limit attestation"})
    blocked = any(f["severity"] == "blocker" for f in findings)
    return {
        "status": "fail" if blocked else "warn" if findings else "pass",
        "risk": risk,
        "findings": findings,
        "attestation": required,
        "rule": "Requested sandbox policy is not evidence; observed runtime facts must satisfy the risk profile.",
    }
