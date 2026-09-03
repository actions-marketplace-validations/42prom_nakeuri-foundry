from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

PACKAGE_SKILLS_INSTALL = ["dart", "run", "skills@", "get", "--all"]

OFFICIAL_INSTALL = [
    ["npx", "skills", "add", "flutter/agent-plugins", "--skill", "*", "--agent", "universal", "--yes"],
    ["npx", "skills", "add", "dart-lang/skills", "--skill", "*", "--agent", "universal", "--yes"],
]


def _hash_tree(path: Path) -> dict[str, str]:
    out = {}
    if not path.exists(): return out
    for p in sorted(x for x in path.rglob("*") if x.is_file()):
        out[p.relative_to(path).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def official_stack_status(root: Path) -> dict[str, Any]:
    root = root.resolve(); skills = root / ".agents" / "skills"; lock = root / ".factory" / "skills-lock.json"
    dart_cfg = False
    mcp = root / ".agents" / "mcp_config.json"
    if mcp.exists():
        try:
            cfg = json.loads(mcp.read_text(encoding="utf-8")); d = cfg.get("mcpServers", {}).get("dart", {})
            dart_cfg = d.get("command") == "dart" and d.get("args") == ["mcp-server"]
        except Exception: pass
    hashes = _hash_tree(skills)
    lock_ok = False
    if lock.exists():
        try: lock_ok = json.loads(lock.read_text(encoding="utf-8")).get("files") == hashes
        except Exception: pass
    package_skill_dirs = []
    for candidate in [root / ".agents" / "skills"]:
        if candidate.exists():
            package_skill_dirs = [p.name for p in candidate.iterdir() if p.is_dir()]
    flutter_available = shutil.which("flutter") is not None
    dart_available = shutil.which("dart") is not None
    ready = dart_cfg and bool(hashes) and lock_ok and flutter_available and dart_available
    return {
        "status": "pass" if ready else "partial",
        "schema": "nakeuri/flutter-official-ai-stack/v2",
        "dart_mcp_configured": dart_cfg,
        "official_skills_present": bool(hashes),
        "skills_lock_present": lock.exists(),
        "skills_lock_valid": lock_ok,
        "flutter_available": flutter_available,
        "dart_available": dart_available,
        "npx_available": shutil.which("npx") is not None,
        "files": len(hashes),
        "package_skill_directories": sorted(package_skill_dirs),
        "readiness_gaps": [
            name for name, ok in {
                "dart_mcp_configured": dart_cfg,
                "official_skills_present": bool(hashes),
                "skills_lock_valid": lock_ok,
                "flutter_available": flutter_available,
                "dart_available": dart_available,
            }.items() if not ok
        ],
        "official_components": {
            "agent_skills": True,
            "dart_flutter_mcp": dart_cfg,
            "developer_knowledge_mcp": "external/optional; configure per supported agent",
            "package_skills": {"command": PACKAGE_SKILLS_INSTALL, "supported": True},
        },
        "rule": "Nakeuri extends the official Flutter AI stack; it does not replace Dart analyzer/MCP authority.",
    }


def lock_skills(root: Path) -> dict[str, Any]:
    root = root.resolve(); files = _hash_tree(root / ".agents" / "skills")
    if not files: return {"status": "fail", "reason": "no skills found under .agents/skills"}
    path = root / ".factory" / "skills-lock.json"; path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema": "foundry/official-skills-lock/v1", "sources": ["flutter/agent-plugins", "dart-lang/skills"], "files": files}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": "pass", "path": str(path), "files": len(files)}


def install_official_skills(root: Path, allow_network: bool = False) -> dict[str, Any]:
    root = root.resolve()
    if not allow_network: return {"status": "blocked", "reason": "network installation requires explicit allow_network=True", "commands": OFFICIAL_INSTALL}
    if not shutil.which("npx"): return {"status": "fail", "reason": "npx not found"}
    runs = []
    for command in OFFICIAL_INSTALL:
        p = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=600)
        runs.append({"command": command, "returncode": p.returncode, "stdout": p.stdout[-4000:], "stderr": p.stderr[-4000:]})
        if p.returncode != 0: return {"status": "fail", "runs": runs}
    return {"status": "pass", "runs": runs, "lock": lock_skills(root), "stack": official_stack_status(root)}


def install_package_skills(root: Path, allow_network: bool = False) -> dict[str, Any]:
    root = root.resolve()
    if not allow_network:
        return {"status": "blocked", "reason": "package skill discovery may access package infrastructure; explicit allow_network=True required", "command": PACKAGE_SKILLS_INSTALL}
    if not shutil.which("dart"):
        return {"status": "fail", "reason": "dart not found"}
    p = subprocess.run(PACKAGE_SKILLS_INSTALL, cwd=root, text=True, capture_output=True, timeout=600)
    return {
        "status": "pass" if p.returncode == 0 else "fail",
        "command": PACKAGE_SKILLS_INSTALL,
        "returncode": p.returncode,
        "stdout": p.stdout[-4000:],
        "stderr": p.stderr[-4000:],
        "lock": lock_skills(root) if p.returncode == 0 and (root / ".agents" / "skills").exists() else None,
    }
