from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .platform_adapters import detect_project_surfaces


def _package_scripts(path: Path) -> dict[str, str]:
    try:
        data = json.loads((path / "package.json").read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in (data.get("scripts") or {}).items()}
    except Exception:
        return {}


def _node_manager(path: Path, *, release: bool = False) -> tuple[str, list[list[str]], list[str]]:
    findings: list[str] = []
    if (path / "pnpm-lock.yaml").exists():
        return "pnpm", [["pnpm", "install", "--frozen-lockfile"]], findings
    if (path / "yarn.lock").exists():
        return "yarn", [["yarn", "install", "--immutable"]], findings
    if (path / "bun.lockb").exists() or (path / "bun.lock").exists():
        return "bun", [["bun", "install", "--frozen-lockfile"]], findings
    if (path / "package-lock.json").exists():
        return "npm", [["npm", "ci"]], findings
    if release:
        findings.append("release Node/Next.js surface has no recognized lockfile")
        return "npm", [], findings
    findings.append("non-release Node/Next.js surface has no lockfile; install is intentionally not invented")
    return "npm", [], findings


def _surface_commands(root: Path, surface: dict[str, Any], profile: str) -> dict[str, Any]:
    release = profile == "release"
    standard = profile in {"standard", "release"}
    path = root if surface["root"] == "." else root / surface["root"]
    sid = surface["id"]
    cmds: list[list[str]] = []
    package_manager = None
    findings: list[str] = []
    if sid == "flutter":
        if release and not (path / "pubspec.lock").exists():
            findings.append("Flutter release surface missing pubspec.lock")
        cmds = [
            ["flutter", "pub", "get"],
            ["dart", "format", "--output=none", "--set-exit-if-changed", "."],
            ["flutter", "analyze"],
        ]
        if standard:
            cmds.append(["flutter", "test"])
        if release:
            cmds.append(["flutter", "build", "appbundle", "--release"])
    elif sid in {"node", "nextjs"}:
        package_manager, install, lock_findings = _node_manager(path, release=release)
        findings.extend(lock_findings)
        cmds.extend(install)
        scripts = _package_scripts(path)
        script_names = ("lint", "typecheck") if profile == "fast" else ("lint", "typecheck", "test") if profile == "standard" else ("lint", "typecheck", "test", "build")
        for name in script_names:
            if name in scripts:
                cmds.append(["npm", "run", name] if package_manager == "npm" else [package_manager, name])
        if release and "build" not in scripts:
            findings.append(f"{sid} release surface has no project-declared build script")
    elif sid == "python":
        if (path / "uv.lock").exists():
            cmds.append(["uv", "sync", "--frozen"])
        elif (path / "poetry.lock").exists():
            cmds.append(["poetry", "install", "--no-interaction", "--sync"])
        elif release:
            findings.append("Python release surface has no uv.lock/poetry.lock; reproducible dependency resolution is not proven")
        elif (path / "pyproject.toml").exists():
            cmds.append(["python", "-m", "pip", "install", "-e", "."])
        elif (path / "requirements.txt").exists():
            cmds.append(["python", "-m", "pip", "install", "-r", "requirements.txt"])
        pyproject = (path / "pyproject.toml").read_text(encoding="utf-8", errors="ignore") if (path / "pyproject.toml").exists() else ""
        if "[tool.ruff" in pyproject:
            cmds.append(["ruff", "check", "."])
        if "[tool.pyright" in pyproject:
            cmds.append(["pyright"])
        uses_pytest = "[tool.pytest" in pyproject or (path / "pytest.ini").exists()
        if standard and uses_pytest:
            cmds.append(["python", "-m", "pytest"])
        elif standard and (path / "tests").exists():
            cmds.append(["python", "-m", "unittest", "discover", "-s", "tests"])
    elif sid == "dotnet":
        cmds = [["dotnet", "restore"], ["dotnet", "build", "--no-restore"]]
        if standard:
            cmds.append(["dotnet", "test", "--no-build"])
    elif sid == "go":
        if release and not (path / "go.sum").exists():
            findings.append("Go release surface missing go.sum")
        cmds = [["go", "vet", "./..."]]
        if standard:
            cmds.append(["go", "test", "./..."])
    elif sid == "rust":
        if release and not (path / "Cargo.lock").exists():
            findings.append("Rust release surface missing Cargo.lock")
        cmds = [["cargo", "fmt", "--check"], ["cargo", "clippy", "--", "-D", "warnings"]]
        if standard:
            cmds.append(["cargo", "test", "--locked"] if release else ["cargo", "test"])
    elif sid == "java":
        if (path / "gradlew").exists():
            cmds = [["./gradlew", "test"]]
        elif (path / "mvnw").exists():
            cmds = [["./mvnw", "test"]]
        elif release:
            findings.append("Java release surface lacks a project wrapper (gradlew/mvnw)")
        elif (path / "pom.xml").exists():
            cmds = [["mvn", "test"]]
        else:
            cmds = [["gradle", "test"]]
    return {"surface": surface, "package_manager": package_manager, "commands": cmds, "findings": findings}


def build_ci_plan(root: Path, profile: str = "standard") -> dict[str, Any]:
    if profile not in {"fast", "standard", "release"}:
        raise ValueError("unsupported CI profile")
    root = root.resolve()
    surfaces = detect_project_surfaces(root)
    plans = [_surface_commands(root, s, profile) for s in surfaces]
    findings = [f"{p['surface']['root']}:{p['surface']['id']}: {x}" for p in plans for x in p.get("findings", [])]
    release_blockers = findings if profile == "release" else []
    return {
        "schema": "nakeuri/ci-plan/v2",
        "status": "fail" if release_blockers else "pass" if plans else "warn",
        "profile": profile,
        "root": str(root),
        "plans": plans,
        "findings": findings,
        "rule": "Commands come from detected native toolchains/manifests. Release plans require reproducible dependency inputs and never invent undeclared project scripts.",
    }
