from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

from . import __version__

DEFAULT_MATRIX = {
    "schema": "nakeuri/compatibility/v1",
    "foundry": {"version": __version__},
    "python": {"min": "3.11", "max_exclusive": "3.14"},
    "mcp": {"min_major": 2, "max_major": 2},
    "flutter": {"policy": "current stable supported; exact project ref should be pinned in CI"},
    "dart": {"policy": "version bundled/compatible with selected Flutter stable"},
    "openhands": {"optional": True, "python_min": "3.12", "min": "1.44.1", "max_exclusive": "2"},
    "antigravity": {"policy": "workspace plugin + MCP + hooks contract must validate at bootstrap"},
}


def _version_tuple(value: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", value)
    return tuple(int(x) for x in nums[:3]) or (0,)


def _pkg(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _tool_version(command: str, args: list[str]) -> dict[str, Any]:
    path = shutil.which(command)
    if not path:
        return {"available": False, "version": None}
    try:
        p = subprocess.run([path, *args], text=True, capture_output=True, timeout=10)
        text = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
        return {"available": True, "returncode": p.returncode, "version": text.splitlines()[0] if text else None}
    except Exception as exc:
        return {"available": True, "version": None, "error": str(exc)}


def compatibility_status(root: Path | None = None) -> dict[str, Any]:
    root = (root or Path.cwd()).resolve()
    findings: list[str] = []
    py = sys.version_info[:3]
    if py < (3, 11):
        findings.append("Python <3.11 is unsupported")
    if py >= (3, 14):
        findings.append("Python >=3.14 is outside the declared compatibility window")
    mcp = _pkg("mcp")
    if mcp is not None and _version_tuple(mcp)[0] != 2:
        findings.append(f"MCP SDK major {mcp} is outside supported major 2")
    oh = _pkg("openhands-sdk")
    if oh is not None:
        if py < (3, 12):
            findings.append("OpenHands SDK requires the optional Python >=3.12 runtime profile")
        if not ((1, 44, 1) <= _version_tuple(oh) < (2,)):
            findings.append(f"OpenHands SDK {oh} is outside tested compatibility range >=1.44.1,<2")
    flutter = _tool_version("flutter", ["--version"])
    dart = _tool_version("dart", ["--version"])
    return {
        "schema": "nakeuri/compatibility-status/v1",
        "status": "unsupported" if findings else ("degraded" if not flutter["available"] or not dart["available"] or mcp is None else "supported"),
        "foundry_version": __version__,
        "python": ".".join(map(str, py)),
        "packages": {"mcp": mcp, "openhands-sdk": oh, "openhands-tools": _pkg("openhands-tools")},
        "tools": {"flutter": flutter, "dart": dart},
        "findings": findings,
        "matrix": DEFAULT_MATRIX,
        "rule": "SUPPORTED means the local toolchain is inside declared version ranges; it does not prove project tests/builds passed.",
    }


def write_compatibility_matrix(root: Path) -> Path:
    path = root.resolve() / ".factory" / "compatibility.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(DEFAULT_MATRIX, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
