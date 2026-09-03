from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .util import ASSET_ROOT


class ComponentError(ValueError):
    pass


RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "release": 3}


class ComponentRegistry:
    def __init__(self, components_dir: Path | None = None):
        self.components_dir = components_dir or (ASSET_ROOT / "registry" / "components")
        self.components: dict[str, dict[str, Any]] = {}
        self.reload()

    def reload(self) -> None:
        self.components.clear()
        if not self.components_dir.exists():
            return
        for path in sorted(self.components_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            self.components[data["id"]] = data

    def list(self) -> list[dict[str, Any]]:
        return [self.components[k] for k in sorted(self.components)]

    def by_capability(self, capability: str) -> list[dict[str, Any]]:
        return [c for c in self.components.values() if capability in c.get("provides", [])]

    def resolve(self, requested: list[str]) -> dict[str, Any]:
        selected: dict[str, dict[str, Any]] = {}
        queue = list(requested)
        reasons: list[str] = []

        while queue:
            item = queue.pop(0)
            if item in selected:
                continue
            comp = self.components.get(item)
            if comp is None:
                providers = self.by_capability(item)
                if not providers:
                    raise ComponentError(f"No component provides '{item}' and no component has that id")
                comp = sorted(providers, key=lambda c: (RISK_ORDER.get(str(c.get("risk", "medium")).lower(), 1), c["id"]))[0]
            if comp["id"] in selected:
                continue
            selected[comp["id"]] = comp
            reasons.append(f"selected {comp['id']}")
            for req in comp.get("requires", []):
                if not any(req in c.get("provides", []) for c in selected.values()):
                    queue.append(req)

        ids = set(selected)
        capabilities = {p for c in selected.values() for p in c.get("provides", [])}
        conflicts = []
        for c in selected.values():
            for conflict in c.get("conflicts", []):
                if conflict in ids or conflict in capabilities:
                    conflicts.append({"component": c["id"], "conflict": conflict})
        if conflicts:
            raise ComponentError(f"Conflicting component plan: {conflicts}")

        # topological-ish order by repeatedly taking satisfied requirements
        ordered: list[str] = []
        provided: set[str] = set()
        remaining = dict(selected)
        while remaining:
            ready = [cid for cid,c in remaining.items() if set(c.get("requires", [])) <= provided]
            if not ready:
                # A dependency may be provided by a peer whose own requirements are unresolved; surface cycle.
                raise ComponentError(f"Dependency cycle or unresolved capabilities: {sorted(remaining)}")
            for cid in sorted(ready):
                c = remaining.pop(cid)
                ordered.append(cid)
                provided.update(c.get("provides", []))

        return {
            "requested": requested,
            "ordered_components": ordered,
            "capabilities": sorted(provided),
            "components": [selected[cid] for cid in ordered],
            "conflicts": conflicts,
            "notes": reasons,
        }
