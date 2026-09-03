from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .delivery import install_delivery_plane
from .safe_paths import resolve_inside
from .util import ASSET_ROOT

MANAGED_WORKFLOWS = ["flutter-pr-ci.yml", "release-gate.yml", "flutter-e2e.yml", "ios-compile.yml"]


def _backup_file(root: Path, path: Path, backup_root: Path) -> str | None:
    if not path.exists(): return None
    rel = path.resolve().relative_to(root.resolve())
    dst = backup_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if path.is_dir(): shutil.copytree(path, dst, dirs_exist_ok=True)
    else: shutil.copy2(path, dst)
    return rel.as_posix()


def upgrade_project(root: Path, *, apply: bool = False) -> dict[str, Any]:
    """Upgrade only Foundry-managed assets; preserve Genome, project rules and app code."""
    root = root.resolve()
    if not (root / ".factory").exists():
        return {"status": "fail", "reason": "project is not bootstrapped with Nakeuri Foundry"}
    managed = [
        ".agents/plugins/nakeuri-flutter-foundry",
        ".agents/mcp_config.json",
        *[f".github/workflows/{x}" for x in MANAGED_WORKFLOWS],
    ]
    plan = {"foundry_version": __version__, "managed": managed, "preserved": ["PROJECT_RULES.md", ".factory/genome", ".factory/graph", "application source"]}
    if not apply:
        return {"status": "planned", "plan": plan}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = root / ".factory" / "backups" / f"upgrade-{stamp}"
    backed_up = []
    for rel in managed:
        p = resolve_inside(root, rel)
        item = _backup_file(root, p, backup_root)
        if item: backed_up.append(item)
    plugin_dst = root / ".agents" / "plugins" / "nakeuri-flutter-foundry"
    if plugin_dst.exists(): shutil.rmtree(plugin_dst)
    plugin_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ASSET_ROOT / "plugin", plugin_dst)
    mcp_path = root / ".agents" / "mcp_config.json"
    existing = {}
    if mcp_path.exists():
        try: existing = json.loads(mcp_path.read_text(encoding="utf-8"))
        except Exception: existing = {}
    servers = existing.setdefault("mcpServers", {})
    servers["dart"] = {"command": "dart", "args": ["mcp-server"]}
    servers["nakeuri-flutter-foundry"] = {"command": "flutter-foundry-mcp", "env": {"FLUTTER_FOUNDRY_WORKSPACE": "."}}
    mcp_path.parent.mkdir(parents=True, exist_ok=True)
    mcp_path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    delivery = install_delivery_plane(root, force=True)
    config = root / ".factory" / "config.json"
    if config.exists():
        data = json.loads(config.read_text(encoding="utf-8")); data["foundry_version"] = __version__
        config.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": "pass", "version": __version__, "backup": str(backup_root), "backed_up": backed_up, "delivery": delivery, "preserved": plan["preserved"]}
