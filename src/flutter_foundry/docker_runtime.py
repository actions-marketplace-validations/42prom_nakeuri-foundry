from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Callable

from .runtime_security import HardenedContainerPolicy, validate_runtime_attestation

Runner = Callable[..., subprocess.CompletedProcess[str]]


def _default_runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, capture_output=True, **kwargs)


def _create_args(policy: HardenedContainerPolicy, workspace: Path, command: list[str], name: str) -> list[str]:
    args = ["docker", "create", "--name", name, "--init", "--user", policy.user]
    if policy.read_only_rootfs:
        args.append("--read-only")
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
    args += ["--mount", f"type=bind,src={workspace.resolve()},dst=/workspace,{mount_mode}", "--workdir", "/workspace"]
    args += [policy.image, *command]
    return args


def _inspect_to_attestation(data: dict[str, Any]) -> dict[str, Any]:
    host = data.get("HostConfig") or {}
    config = data.get("Config") or {}
    security = host.get("SecurityOpt") or []
    cap_drop = host.get("CapDrop") or []
    memory_bytes = int(host.get("Memory") or 0)
    nano_cpus = int(host.get("NanoCpus") or 0)
    return {
        "image": data.get("Image") or config.get("Image"),
        "user": config.get("User"),
        "read_only_rootfs": bool(host.get("ReadonlyRootfs")),
        "cap_drop_all": "ALL" in cap_drop,
        "no_new_privileges": any(str(x).lower() == "no-new-privileges:true" for x in security),
        "network_mode": host.get("NetworkMode"),
        "memory_mb": round(memory_bytes / (1024 * 1024)) if memory_bytes else 0,
        "cpus": nano_cpus / 1_000_000_000 if nano_cpus else 0,
        "pids_limit": host.get("PidsLimit"),
    }


class DockerExecutor:
    """Real Docker execution path with observed-runtime attestation.

    The executor uses create -> inspect -> start -> inspect -> remove instead of
    trusting requested flags. Tests can inject a runner; production uses the
    Docker CLI when installed.
    """

    def __init__(self, runner: Runner = _default_runner):
        self.runner = runner

    def available(self) -> bool:
        return shutil.which("docker") is not None if self.runner is _default_runner else True

    def execute(self, policy: HardenedContainerPolicy, workspace: Path, command: list[str], *, timeout: int = 1800) -> dict[str, Any]:
        if not self.available():
            return {"status": "unavailable", "reason": "docker CLI missing"}
        if not workspace.resolve().exists():
            return {"status": "fail", "reason": "workspace missing"}
        name = f"nakeuri-{uuid.uuid4().hex[:12]}"
        created = self.runner(_create_args(policy, workspace, command, name), timeout=60)
        if created.returncode != 0:
            return {"status": "fail", "phase": "create", "stderr": created.stderr[-4000:]}
        container_id = created.stdout.strip() or name
        try:
            inspected = self.runner(["docker", "inspect", container_id], timeout=30)
            if inspected.returncode != 0:
                return {"status": "fail", "phase": "inspect", "stderr": inspected.stderr[-4000:]}
            parsed = json.loads(inspected.stdout)[0]
            attestation = _inspect_to_attestation(parsed)
            security = validate_runtime_attestation(attestation, policy.risk)
            if security["status"] == "fail":
                return {"status": "fail", "phase": "pre-start-security", "runtime_attestation": attestation, "security": security}
            started = self.runner(["docker", "start", "-a", container_id], timeout=timeout)
            state = self.runner(["docker", "inspect", "--format", "{{json .State}}", container_id], timeout=30)
            state_data: dict[str, Any] = {}
            if state.returncode == 0 and state.stdout.strip():
                try:
                    state_data = json.loads(state.stdout.strip())
                except Exception:
                    state_data = {"raw": state.stdout.strip()}
            exit_code = int(state_data.get("ExitCode", started.returncode)) if isinstance(state_data, dict) else started.returncode
            return {
                "status": "pass" if exit_code == 0 else "fail",
                "provider": "docker",
                "container_id": container_id,
                "exit_code": exit_code,
                "stdout_tail": started.stdout[-8000:],
                "stderr_tail": started.stderr[-8000:],
                "runtime_attestation": attestation,
                "security": security,
                "state": state_data,
            }
        finally:
            try:
                self.runner(["docker", "rm", "-f", container_id], timeout=30)
            except Exception:
                pass
