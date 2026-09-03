from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


def patrol_status(root: Path) -> dict[str, Any]:
    app=root if (root/"pubspec.yaml").exists() else root/"mobile" if (root/"mobile"/"pubspec.yaml").exists() else root
    pub=(app/"pubspec.yaml").read_text(encoding="utf-8",errors="ignore") if (app/"pubspec.yaml").exists() else ""
    configured="patrol:" in pub or "patrol_test:" in pub or (app/"patrol.yaml").exists()
    exe=shutil.which("patrol")
    return {"status":"pass" if configured and exe else "unavailable" if configured else "not_configured","configured":configured,"executable":exe,"app_root":str(app)}


def run_patrol(root: Path, *, target: str|None=None, device: str|None=None, timeout: int=1800) -> dict[str, Any]:
    st=patrol_status(root);app=Path(st["app_root"])
    if st["status"]!="pass": return {**st,"reason":"Patrol must be configured in the Flutter app and installed on PATH"}
    cmd=["patrol","test"]
    if target:cmd += ["--target",target]
    if device:cmd += ["--device",device]
    start=time.monotonic()
    try:
        p=subprocess.run(cmd,cwd=app,text=True,capture_output=True,timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status":"fail","command":cmd,"reason":f"timeout after {timeout}s"}
    out=(p.stdout+"\n"+p.stderr).strip()
    result={"status":"pass" if p.returncode==0 else "fail","command":cmd,"returncode":p.returncode,"duration_ms":int((time.monotonic()-start)*1000),"summary":"\n".join(out.splitlines()[-80:])[-12000:]}
    evidence=app/".factory"/"evidence"/"patrol-runtime.json";evidence.parent.mkdir(parents=True,exist_ok=True)
    evidence.write_text(json.dumps({"schema":"nakeuri/patrol-runtime-evidence/v1",**result},indent=2)+"\n",encoding="utf-8")
    result["evidence_path"]=str(evidence)
    return result
