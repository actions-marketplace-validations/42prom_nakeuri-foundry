from __future__ import annotations

from pathlib import Path
from typing import Any

from .project_inspector import inspect_project
from .util import safe_rel

FORBIDDEN_GLOBALS = ["services", "repositories", "controllers", "utils"]


def architecture_scan(root: Path) -> dict[str, Any]:
    root = root.resolve()
    info = inspect_project(root)
    findings = []
    lib_roots = [p for p in [root / "lib", root / "mobile" / "lib"] if p.exists()]
    for lib in lib_roots:
        for name in FORBIDDEN_GLOBALS:
            p = lib / name
            if p.exists() and any(x.is_file() for x in p.rglob("*")):
                findings.append({
                    "rule": "global-dumping-ground",
                    "severity": "medium",
                    "path": safe_rel(p, root),
                    "message": f"Global {name}/ exists. Verify it is explicitly justified by PROJECT_RULES.md; feature-owned logic should remain feature-owned."
                })
    hints = info.get("architecture_hints", {})
    if hints.get("riverpod") and hints.get("bloc"):
        findings.append({
            "rule":"multiple-state-systems",
            "severity":"high",
            "path":"pubspec.yaml",
            "message":"Riverpod and BLoC dependencies are both present. A project should use one primary state system unless PROJECT_RULES.md explicitly approves the exception."
        })
    status = "fail" if any(f["severity"] == "high" for f in findings) else "warn" if findings else "pass"
    return {"status":status,"findings":findings,"summary":{"total":len(findings),"high":sum(f["severity"]=="high" for f in findings),"medium":sum(f["severity"]=="medium" for f in findings)}}
