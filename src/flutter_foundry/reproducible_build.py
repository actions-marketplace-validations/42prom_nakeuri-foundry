from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path
from typing import Any


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _wheel_once(root: Path, out: Path, epoch: str) -> dict[str, Any]:
    env = os.environ.copy(); env["SOURCE_DATE_EPOCH"] = epoch; env["PYTHONHASHSEED"] = "0"
    p = subprocess.run([sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--no-build-isolation", "-w", str(out)], cwd=root, text=True, capture_output=True, timeout=180, env=env)
    wheels = sorted(out.glob("*.whl"))
    return {"status": "pass" if p.returncode == 0 and len(wheels) == 1 else "fail", "returncode": p.returncode, "output": ((p.stdout or "") + "\n" + (p.stderr or ""))[-5000:], "wheel": str(wheels[0]) if len(wheels) == 1 else None, "sha256": _sha(wheels[0]) if len(wheels) == 1 else None}


def reproducible_build_check(root: Path, install_smoke: bool = True) -> dict[str, Any]:
    root = root.resolve()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td); a = td / "a"; b = td / "b"; a.mkdir(); b.mkdir()
        first = _wheel_once(root, a, "1700000000"); second = _wheel_once(root, b, "1700000000")
        same = first.get("status") == "pass" and second.get("status") == "pass" and first.get("sha256") == second.get("sha256")
        smoke: dict[str, Any] = {"status": "skipped"}
        if same and install_smoke:
            envdir = td / "venv"; venv.EnvBuilder(with_pip=True, clear=True).create(envdir)
            python = envdir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            wheel = str(first["wheel"])
            clean_env = os.environ.copy()
            clean_env.pop("PYTHONPATH", None)
            clean_env.pop("PYTHONHOME", None)
            install = subprocess.run([str(python), "-m", "pip", "install", "--no-deps", "--force-reinstall", wheel], text=True, capture_output=True, timeout=120, env=clean_env)
            probe = subprocess.run([str(python), "-I", "-c", "import flutter_foundry; print(flutter_foundry.__version__)"], text=True, capture_output=True, timeout=30, env=clean_env) if install.returncode == 0 else None
            smoke = {"status": "pass" if probe and probe.returncode == 0 else "fail", "install_returncode": install.returncode, "probe_returncode": probe.returncode if probe else None, "version": probe.stdout.strip() if probe else None, "output": ((install.stdout or "") + (install.stderr or "") + ((probe.stdout or "") + (probe.stderr or "") if probe else ""))[-5000:]}
        return {"status": "pass" if same and (not install_smoke or smoke.get("status") == "pass") else "fail", "reproducible": same, "first": first, "second": second, "install_smoke": smoke}
