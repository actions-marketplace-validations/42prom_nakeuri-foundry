from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PlatformAdapter:
    id: str
    maturity: str
    authoritative_tools: tuple[str, ...]
    semantic_providers: tuple[str, ...]
    manifests: tuple[str, ...]
    fast_checks: tuple[tuple[str, ...], ...] = ()
    standard_checks: tuple[tuple[str, ...], ...] = ()
    release_checks: tuple[tuple[str, ...], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {k: [list(x) for x in v] if k.endswith("checks") else list(v) if isinstance(v, tuple) else v for k, v in data.items()}


FLUTTER = PlatformAdapter(
    id="flutter", maturity="flagship",
    authoritative_tools=("dart mcp-server", "official Flutter agent skills", "official Dart agent skills", "Flutter SDK"),
    semantic_providers=("Dart analyzer", "Dart/Flutter MCP"), manifests=("pubspec.yaml",),
    fast_checks=(("dart", "format", "--output=none", "--set-exit-if-changed", "."), ("flutter", "analyze")),
    standard_checks=(("flutter", "test"),), release_checks=(("flutter", "build", "appbundle", "--release"),),
)
NODE = PlatformAdapter(
    id="node", maturity="standard",
    authoritative_tools=("project-declared package scripts", "TypeScript compiler when configured"),
    semantic_providers=("TypeScript language service",), manifests=("package.json",),
)
NEXTJS = PlatformAdapter(
    id="nextjs", maturity="specialist",
    authoritative_tools=("Next.js project scripts", "TypeScript compiler", "ESLint", "Playwright when configured"),
    semantic_providers=("TypeScript language service", "Next.js build diagnostics"), manifests=("package.json", "next.config.*"),
)
PYTHON = PlatformAdapter(
    id="python", maturity="standard",
    authoritative_tools=("pyproject/project-declared tooling", "pytest", "Ruff when configured", "Pyright when configured"),
    semantic_providers=("Pyright/Python language server", "AST"), manifests=("pyproject.toml", "requirements.txt"),
)
DOTNET = PlatformAdapter(
    id="dotnet", maturity="standard",
    authoritative_tools=("dotnet CLI", "Roslyn", "NuGet"), semantic_providers=("Roslyn",), manifests=("*.csproj", "*.sln"),
)
GO = PlatformAdapter(
    id="go", maturity="standard",
    authoritative_tools=("go toolchain", "go vet", "go test"), semantic_providers=("gopls",), manifests=("go.mod",),
)
RUST = PlatformAdapter(
    id="rust", maturity="standard",
    authoritative_tools=("cargo", "rustc", "clippy"), semantic_providers=("rust-analyzer",), manifests=("Cargo.toml",),
)
JAVA = PlatformAdapter(
    id="java", maturity="standard",
    authoritative_tools=("project Gradle/Maven wrapper", "JDK"), semantic_providers=("Java language server/compiler"), manifests=("pom.xml", "build.gradle", "build.gradle.kts"),
)

ADAPTERS = {a.id: a for a in [FLUTTER, NODE, NEXTJS, PYTHON, DOTNET, GO, RUST, JAVA]}


def _read_package_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _candidate_roots(root: Path) -> list[Path]:
    roots = [root]
    for child in sorted(root.iterdir()) if root.exists() else []:
        if child.is_dir() and child.name not in {".git", ".factory", "node_modules", ".dart_tool", "build", "dist", ".next", ".venv", "venv"}:
            roots.append(child)
    return roots


def _surface_for(path: Path, root: Path) -> list[dict[str, Any]]:
    rel = "." if path == root else path.relative_to(root).as_posix()
    out: list[dict[str, Any]] = []
    manifests: list[str] = []
    if (path / "pubspec.yaml").exists():
        manifests.append("pubspec.yaml"); out.append({"id": "flutter", "root": rel, "maturity": FLUTTER.maturity, "manifests": manifests.copy()})
    package = path / "package.json"
    if package.exists():
        data = _read_package_json(package); deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
        nid = "nextjs" if "next" in deps else "node"
        out.append({"id": nid, "root": rel, "maturity": ADAPTERS[nid].maturity, "manifests": ["package.json"]})
    if (path / "pyproject.toml").exists() or (path / "requirements.txt").exists():
        ms = [x for x in ("pyproject.toml", "requirements.txt") if (path / x).exists()]
        out.append({"id": "python", "root": rel, "maturity": PYTHON.maturity, "manifests": ms})
    cs = list(path.glob("*.csproj")); sln = list(path.glob("*.sln"))
    if cs or sln:
        out.append({"id": "dotnet", "root": rel, "maturity": DOTNET.maturity, "manifests": [p.name for p in cs + sln]})
    if (path / "go.mod").exists(): out.append({"id": "go", "root": rel, "maturity": GO.maturity, "manifests": ["go.mod"]})
    if (path / "Cargo.toml").exists(): out.append({"id": "rust", "root": rel, "maturity": RUST.maturity, "manifests": ["Cargo.toml"]})
    j = [x for x in ("pom.xml", "build.gradle", "build.gradle.kts") if (path / x).exists()]
    if j: out.append({"id": "java", "root": rel, "maturity": JAVA.maturity, "manifests": j})
    return out


def detect_project_surfaces(root: Path) -> list[dict[str, Any]]:
    root = root.resolve(); seen = set(); out = []
    for candidate in _candidate_roots(root):
        for s in _surface_for(candidate, root):
            key = (s["id"], s["root"])
            if key not in seen:
                seen.add(key); out.append(s)
    return out


def detect_platforms(root: Path) -> list[str]:
    """Backward-compatible coarse platform IDs.

    nextjs intentionally collapses into node here; detailed callers should use
    detect_project_surfaces().
    """
    surfaces = detect_project_surfaces(root); ids = []
    for preferred in ["flutter", "node", "python", "dotnet", "go", "rust", "java"]:
        if preferred == "node":
            present = any(s["id"] in {"node", "nextjs"} for s in surfaces)
        else:
            present = any(s["id"] == preferred for s in surfaces)
        if present: ids.append(preferred)
    return ids


def adapter_report(root: Path) -> dict[str, Any]:
    ids = detect_platforms(root); surfaces = detect_project_surfaces(root)
    detailed_ids = sorted({s["id"] for s in surfaces})
    return {
        "status": "pass" if surfaces else "warn",
        "platforms": ids,
        "surfaces": surfaces,
        "adapters": [ADAPTERS[i].to_dict() for i in detailed_ids],
        "rule": "Universal core, deep specialist adapters. Existing project tooling is authoritative before Foundry invents commands.",
    }
