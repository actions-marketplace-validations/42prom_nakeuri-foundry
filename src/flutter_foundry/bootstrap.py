from __future__ import annotations

import json
import shutil
from pathlib import Path
from .util import ASSET_ROOT
from .genome import init_genome
from .delivery import install_delivery_plane
from .production import init_production_ops
from .visual_regression import init_visual_contract
from .store_delivery import init_store_delivery
from .compatibility import write_compatibility_matrix
from .platform_adapters import detect_project_surfaces
from .standards import init_standards_radar
from .production_graph import init_release_graph
from .knowledge_graph import write_project_graph
from . import __version__
from .antigravity_native import install_antigravity_team


def _copytree(src: Path, dst: Path):
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _ensure_gitignore(root: Path) -> None:
    p = root / ".gitignore"
    existing = p.read_text(encoding="utf-8") if p.exists() else ""
    block = """
# Nakeuri Flutter Foundry runtime artifacts
.factory/orchestration/*.db*
.factory/worktrees/
.factory/reviews/
.factory/evidence/
.factory/proofs/
.factory/assurance/
.factory/runs/
.factory/agent-output/
""".lstrip()
    if "# Nakeuri Flutter Foundry runtime artifacts" not in existing:
        p.write_text(existing + ("\n" if existing and not existing.endswith("\n") else "") + block, encoding="utf-8")


def bootstrap_project(root: Path, force_plugin: bool = True, install_delivery: bool = True) -> dict:
    root = root.resolve()
    surfaces = detect_project_surfaces(root)
    if not surfaces:
        raise ValueError(f"{root} does not look like a supported software project")
    agents = root / ".agents"; agents.mkdir(parents=True, exist_ok=True)
    native_team = install_antigravity_team(root, overwrite=force_plugin)
    plugin_src = ASSET_ROOT / "plugin"; plugin_dst = agents / "plugins" / "nakeuri-flutter-foundry"
    if force_plugin or not plugin_dst.exists(): _copytree(plugin_src, plugin_dst)
    servers = {"nakeuri-flutter-foundry": {"command": "flutter-foundry-mcp", "env": {"FLUTTER_FOUNDRY_WORKSPACE": "."}}}
    if any(x["id"] == "flutter" for x in surfaces):
        servers["dart"] = {"command": "dart", "args": ["mcp-server"]}
    mcp = {"mcpServers": servers}
    (agents / "mcp_config.json").write_text(json.dumps(mcp, indent=2) + "\n", encoding="utf-8")
    vscode_mcp = None
    if any(x["id"] == "flutter" for x in surfaces):
        vscode = root / ".vscode"; vscode.mkdir(parents=True, exist_ok=True); vscode_mcp = vscode / "mcp.json"
        existing = {}
        if vscode_mcp.exists():
            try: existing = json.loads(vscode_mcp.read_text(encoding="utf-8"))
            except Exception: existing = {}
        existing_servers = existing.get("servers", {}) if isinstance(existing, dict) and isinstance(existing.get("servers", {}), dict) else {}
        existing_servers.setdefault("dart", {"command":"dart","args":["mcp-server"]})
        existing = {**existing, "servers": existing_servers}
        vscode_mcp.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    rules = root / "PROJECT_RULES.md"; created_rules = False
    if not rules.exists(): shutil.copy2(ASSET_ROOT / "PROJECT_RULES.template.md", rules); created_rules = True
    factory = root / ".factory"
    for d in ["memory", "proofs", "evidence", "graph", "orchestration", "worktrees", "reviews", "assurance", "runs", "agent-output"]: (factory / d).mkdir(parents=True, exist_ok=True)
    config = factory / "config.json"
    if not config.exists():
        config.write_text(json.dumps({
            "schema": "nakeuri-flutter-foundry/project/v3",
            "verification_profile": "standard",
            "human_merge_for_high_risk": True,
            "proof_required_for_merge": True,
            "independent_review_for_high_risk": True,
            "single_source_of_truth": True,
            "platform_adapters": sorted({x["id"] for x in surfaces}),
            "foundry_version": __version__,
        }, indent=2) + "\n", encoding="utf-8")
    genome = init_genome(root)
    cap = factory / "graph" / "capabilities.json"; inv = factory / "graph" / "invariants.json"
    if not cap.exists(): cap.write_text(json.dumps({"schema": "foundry/capability-graph/v1", "capabilities": {}, "facts": {}, "journeys": {}}, indent=2) + "\n", encoding="utf-8")
    if not inv.exists(): inv.write_text(json.dumps({"schema": "foundry/invariants/v1", "invariants": {}}, indent=2) + "\n", encoding="utf-8")
    intent = factory / "change-intent.example.json"
    if not intent.exists(): intent.write_text(json.dumps({"schema": "foundry/change-intent/v1", "task": "describe change", "base": "HEAD~1", "allowed_globs": ["lib/**", "test/**"], "must_not_change_globs": [".factory/genome/**"]}, indent=2) + "\n", encoding="utf-8")
    production = init_production_ops(root)
    store_delivery = init_store_delivery(root)
    visual = init_visual_contract(root)
    compatibility = write_compatibility_matrix(root)
    standards = init_standards_radar(root)
    release_graph = init_release_graph(root)
    software_graph = write_project_graph(root)
    delivery = install_delivery_plane(root) if install_delivery else {"status": "skipped"}
    _ensure_gitignore(root)
    return {"project": str(root), "native_team": native_team, "plugin": str(plugin_dst), "mcp_config": str(agents / "mcp_config.json"), "vscode_mcp": str(vscode_mcp) if vscode_mcp else None, "project_rules_created": created_rules, "factory_config": str(config), "genome": genome, "production_contract": str(production), "store_delivery_contract": str(store_delivery), "visual_contract": str(visual), "compatibility": str(compatibility), "standards": str(standards), "release_graph": str(release_graph), "software_graph": str(software_graph), "platform_surfaces": surfaces, "delivery": delivery}
