from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class Runtime(Protocol):
    def execute(self, workspace: Path, command: list[str], timeout: int = 1800) -> dict[str, Any]: ...


@dataclass
class CommandRuntime:
    allow_network: bool = False

    def execute(self, workspace: Path, command: list[str], timeout: int = 1800) -> dict[str, Any]:
        if not command: raise ValueError("command required")
        env = os.environ.copy()
        env["FOUNDRY_NETWORK_POLICY"] = "allow" if self.allow_network else "restricted"
        try:
            p = subprocess.run(command, cwd=workspace, text=True, capture_output=True, timeout=timeout, env=env)
            return {"status": "pass" if p.returncode == 0 else "fail", "returncode": p.returncode, "stdout": p.stdout[-20000:], "stderr": p.stderr[-20000:]}
        except subprocess.TimeoutExpired as e:
            return {"status": "fail", "returncode": None, "timeout": True, "stdout": (e.stdout or "")[-20000:] if isinstance(e.stdout, str) else "", "stderr": (e.stderr or "")[-20000:] if isinstance(e.stderr, str) else ""}


@dataclass
class DryRunRuntime:
    def execute(self, workspace: Path, command: list[str], timeout: int = 1800) -> dict[str, Any]:
        return {"status": "simulated", "workspace": str(workspace), "command": command, "timeout": timeout}
