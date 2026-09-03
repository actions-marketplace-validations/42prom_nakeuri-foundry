from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _run(root: Path, name: str, command: list[str], report: Path, timeout: int = 900) -> dict[str, Any]:
    report.parent.mkdir(parents=True, exist_ok=True)
    try:
        p = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"name": name, "status": "fail", "reason": f"timeout after {timeout}s", "command": command}
    # Some scanners write their report themselves; OSV output is captured below.
    if name == "osv-scanner" and p.stdout:
        report.write_text(p.stdout, encoding="utf-8")
    return {
        "name": name,
        "status": "pass" if p.returncode == 0 else "fail",
        "returncode": p.returncode,
        "command": command,
        "report": str(report) if report.exists() else None,
        "stdout_tail": p.stdout[-4000:],
        "stderr_tail": p.stderr[-4000:],
    }


def run_security_assurance(root: Path, release: bool = False) -> dict[str, Any]:
    """Run authoritative external scanners when installed; never fake their evidence.

    Gitleaks covers repository/history secret leakage. OSV-Scanner V2 covers known
    dependency vulnerabilities. Missing tools become explicit evidence gaps on release.
    """

    root = root.resolve(); out = root / ".factory" / "evidence" / "security"
    scans: list[dict[str, Any]] = []; missing: list[str] = []

    gitleaks = shutil.which("gitleaks")
    if gitleaks:
        report = out / "gitleaks.json"
        scans.append(_run(root, "gitleaks", [gitleaks, "detect", "--source", ".", "--redact", "--no-banner", "--report-format", "json", "--report-path", str(report)], report))
    else:
        missing.append("gitleaks")

    osv = shutil.which("osv-scanner")
    if osv:
        report = out / "osv-scanner.json"
        scans.append(_run(root, "osv-scanner", [osv, "scan", "source", "--format=json", "--recursive", "."], report))
    else:
        missing.append("osv-scanner")

    failed = [s for s in scans if s.get("status") == "fail"]
    if failed:
        status = "fail"
    elif release and missing:
        status = "pass_with_gaps"
    else:
        status = "pass"
    return {
        "status": status,
        "release": release,
        "scans": scans,
        "missing_tools": missing,
        "findings": [f"external scanner failed: {s['name']}" for s in failed] + ([f"release evidence missing tool: {x}" for x in missing] if release else []),
        "rule": "External scanner absence is never represented as PASS release evidence.",
    }
