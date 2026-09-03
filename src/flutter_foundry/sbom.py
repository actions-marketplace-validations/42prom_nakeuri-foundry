from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _purl(name: str, version: str) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "-", name)
    safe_version = re.sub(r"[^A-Za-z0-9._+~-]", "-", version)
    return f"pkg:pub/{safe_name}@{safe_version}"


def cyclonedx_from_pub_deps(data: dict[str, Any]) -> dict[str, Any]:
    """Convert ``dart pub deps --json`` output into a CycloneDX 1.6 dependency BOM.

    Pub is the authoritative resolver. Foundry does not invent package versions or
    dependency edges; missing fields remain absent rather than guessed.
    """

    packages = data.get("packages")
    if not isinstance(packages, list) or not packages:
        raise ValueError("pub deps JSON must contain a non-empty packages list")
    by_name: dict[str, dict[str, Any]] = {}
    components = []
    for pkg in packages:
        if not isinstance(pkg, dict) or not pkg.get("name"):
            continue
        name = str(pkg["name"]); version = str(pkg.get("version") or "0.0.0-unknown")
        ref = _purl(name, version)
        by_name[name] = {**pkg, "_ref": ref}
        comp = {"type": "library", "bom-ref": ref, "name": name, "version": version, "purl": ref}
        source = pkg.get("source")
        if source is not None: comp["properties"] = [{"name": "pub:source", "value": str(source)}]
        components.append(comp)
    if not components:
        raise ValueError("pub deps JSON contained no usable package records")

    roots = [str(x) for x in data.get("roots", []) if str(x) in by_name]
    root_name = roots[0] if roots else str(packages[0].get("name"))
    root_pkg = by_name.get(root_name)
    if root_pkg:
        for comp in components:
            if comp["name"] == root_name:
                comp["type"] = "application"
                break

    dependencies = []
    for name, pkg in by_name.items():
        refs = []
        for key in ("dependencies", "devDependencies"):
            values = pkg.get(key, [])
            if isinstance(values, dict): values = list(values)
            if not isinstance(values, list): continue
            for dep in values:
                dep_name = str(dep)
                if dep_name in by_name:
                    refs.append(by_name[dep_name]["_ref"])
        dependencies.append({"ref": pkg["_ref"], "dependsOn": sorted(set(refs))})

    metadata_component = None
    if root_pkg:
        metadata_component = {"type": "application", "bom-ref": root_pkg["_ref"], "name": root_name, "version": str(root_pkg.get("version") or "0.0.0-unknown")}
    metadata: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tools": {"components": [{"type": "application", "name": "Nakeuri Flutter Foundry", "version": "2.x"}]},
    }
    if metadata_component: metadata["component"] = metadata_component
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": metadata,
        "components": components,
        "dependencies": dependencies,
    }


def generate_cyclonedx_from_pub_deps(input_path: Path, output_path: Path) -> dict[str, Any]:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    bom = cyclonedx_from_pub_deps(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(bom, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": "pass", "output": str(output_path), "components": len(bom["components"]), "dependency_nodes": len(bom["dependencies"]), "format": "CycloneDX 1.6"}
