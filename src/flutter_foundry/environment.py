from __future__ import annotations

import importlib.util
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ModuleNotFoundError, ValueError):
        return False

def _tool(name: str) -> dict[str, Any]:
    path=shutil.which(name)
    return {"available": bool(path), "path": path}

def _docker() -> dict[str, Any]:
    path=shutil.which("docker")
    if not path: return {"available":False,"daemon":False,"path":None}
    try:
        p=subprocess.run([path,"info","--format","{{json .ServerVersion}}"],text=True,capture_output=True,timeout=8)
        return {"available":True,"daemon":p.returncode==0,"path":path,"detail":(p.stdout or p.stderr).strip()[-500:]}
    except Exception as exc:
        return {"available":True,"daemon":False,"path":path,"detail":str(exc)}

def environment_status(root: Path | None = None, probe_docker: bool = False) -> dict[str, Any]:
    root=(root or Path.cwd()).resolve()
    tools={name:_tool(name) for name in ["git","dart","flutter","npx","node","npm","pnpm","yarn","uv","pyright","ruff","pytest","dotnet","go","gopls","rustc","cargo","rust-analyzer","java","javac","gradle","gitleaks","osv-scanner","semgrep","trivy","syft","grype","checkov","zizmor","actionlint","cosign","fastlane","bundle","xcodebuild","adb","kubectl","terraform","tofu"]}
    packages={
        "mcp": _module_available("mcp"),
        "openhands_sdk": _module_available("openhands.sdk"),
        "openhands_tools": _module_available("openhands.tools"),
    }
    docker=_docker() if probe_docker else {**_tool("docker"),"daemon":"not_probed"}
    # Backward-compatible flagship readiness: existing clients historically read core_missing.
    core_missing=[x for x in ["git","dart","flutter"] if not tools[x]["available"]]
    if not packages["mcp"]: core_missing.append("mcp-python-sdk")
    universal_core_missing=[x for x in ["git"] if not tools[x]["available"]]
    flutter_profile_missing=[x for x in ["dart","flutter"] if not tools[x]["available"]]
    if not packages["mcp"]: flutter_profile_missing.append("mcp-python-sdk")
    return {
        "status":"ready" if not core_missing else "partial",
        "root":str(root),
        "python":sys.version.split()[0],
        "os":platform.platform(),
        "tools":tools,
        "packages":packages,
        "docker":docker,
        "core_missing":core_missing,
        "universal_core_missing":universal_core_missing,
        "universal_core_status":"ready" if not universal_core_missing else "partial",
        "flutter_profile_missing":flutter_profile_missing,
        "flutter_profile_status":"ready" if not flutter_profile_missing else "partial",
        "release_gaps":[x for x in ["gitleaks","osv-scanner","fastlane"] if not tools[x]["available"]],
        "ios_host_ready":platform.system()=="Darwin" and tools["xcodebuild"]["available"],
        "rule":"Availability is environment readiness, not proof that a build, E2E flow, scanner, store upload, or production release succeeded.",
    }
