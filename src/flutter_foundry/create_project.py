from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .bootstrap import bootstrap_project


def create_project(path: Path, org: str = "com.example", platforms: str = "android,ios") -> dict:
    path = path.expanduser().resolve()
    flutter = shutil.which("flutter")
    if not flutter:
        raise RuntimeError("flutter executable not found on PATH")
    if path.exists() and any(path.iterdir()):
        raise ValueError(f"target directory is not empty: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [flutter, "create", "--org", org, "--platforms", platforms, str(path)]
    p = subprocess.run(cmd, text=True, capture_output=True, timeout=600)
    if p.returncode != 0:
        raise RuntimeError((p.stdout + "\n" + p.stderr).strip())
    result = bootstrap_project(path)
    result["flutter_create"] = {"command":" ".join(cmd),"status":"pass"}
    return result
