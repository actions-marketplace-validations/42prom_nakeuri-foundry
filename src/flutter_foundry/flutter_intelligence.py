from __future__ import annotations

import re
from pathlib import Path
from typing import Any

IGNORE = {".git", ".dart_tool", "build", "ios/Pods", "android/.gradle"}


def _dart_files(root: Path) -> list[Path]:
    return [p for p in sorted(root.rglob("*.dart")) if p.is_file() and not any(part in IGNORE for part in p.parts)]


def _frameworks(pubspec: str) -> list[str]:
    checks = {
        "riverpod": r"\b(?:flutter_riverpod|hooks_riverpod|riverpod)\s*:",
        "bloc": r"\b(?:flutter_bloc|bloc)\s*:",
        "provider": r"\bprovider\s*:",
        "getx": r"\bget\s*:",
        "go_router": r"\bgo_router\s*:",
        "auto_route": r"\bauto_route\s*:",
    }
    return sorted(name for name, pattern in checks.items() if re.search(pattern, pubspec))


def _async_context_findings(path: Path, root: Path, text: str) -> list[dict[str, Any]]:
    findings = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "await " not in line:
            continue
        window = "\n".join(lines[i + 1:i + 8])
        context_used = bool(re.search(r"\b(?:context|Navigator\.of\(context\)|ScaffoldMessenger\.of\(context\)|Theme\.of\(context\))", window))
        guarded = "context.mounted" in window or re.search(r"\bmounted\b", window)
        if context_used and not guarded:
            findings.append({
                "severity": "medium",
                "rule": "async-build-context",
                "path": path.relative_to(root).as_posix(),
                "line": i + 1,
                "message": "BuildContext appears to be used after an await without a nearby mounted guard.",
            })
    return findings


def _routes(text: str, rel: str) -> list[dict[str, Any]]:
    out = []
    for m in re.finditer(r"\bGoRoute\s*\([^)]*?path\s*:\s*['\"]([^'\"]+)['\"]", text, re.S):
        out.append({"kind": "go_router", "path": m.group(1), "source": rel, "line": text.count("\n", 0, m.start()) + 1})
    return out


def _state_symbols(text: str, rel: str) -> list[dict[str, Any]]:
    patterns = [
        ("riverpod-provider", r"\b([A-Za-z_]\w*Provider)\s*="),
        ("bloc", r"\bclass\s+([A-Za-z_]\w*(?:Bloc|Cubit))\b"),
        ("change-notifier", r"\bclass\s+([A-Za-z_]\w*)\s+extends\s+ChangeNotifier\b"),
    ]
    out = []
    for kind, pat in patterns:
        for m in re.finditer(pat, text):
            out.append({"kind": kind, "name": m.group(1), "source": rel, "line": text.count("\n", 0, m.start()) + 1})
    return out


def flutter_specialist_snapshot(root: Path) -> dict[str, Any]:
    root = root.resolve()
    pubspec_path = root / "pubspec.yaml"
    if not pubspec_path.exists():
        candidates = list(root.glob("*/pubspec.yaml"))
        pubspec_path = candidates[0] if candidates else pubspec_path
    if not pubspec_path.exists():
        return {"status": "not_applicable", "schema": "nakeuri/flutter-specialist/v1", "reason": "pubspec.yaml not found"}
    flutter_root = pubspec_path.parent
    pubspec = pubspec_path.read_text(encoding="utf-8", errors="replace")
    files = _dart_files(flutter_root)
    routes: list[dict[str, Any]] = []
    state: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    platform_channels: list[dict[str, Any]] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(flutter_root).as_posix()
        routes.extend(_routes(text, rel))
        state.extend(_state_symbols(text, rel))
        findings.extend(_async_context_findings(path, flutter_root, text))
        for m in re.finditer(r"\b(?:MethodChannel|EventChannel|BasicMessageChannel)\s*\(\s*['\"]([^'\"]+)['\"]", text):
            platform_channels.append({"channel": m.group(1), "source": rel, "line": text.count("\n", 0, m.start()) + 1})
    frameworks = _frameworks(pubspec)
    return {
        "status": "pass",
        "schema": "nakeuri/flutter-specialist/v1",
        "root": str(flutter_root),
        "dart_files": len(files),
        "frameworks": frameworks,
        "routes": routes,
        "state_symbols": state,
        "platform_channels": platform_channels,
        "findings": findings,
        "risk_summary": {
            "async_context": sum(1 for f in findings if f["rule"] == "async-build-context"),
            "platform_channels": len(platform_channels),
        },
        "targeted_checks": ["dart format --output=none --set-exit-if-changed .", "flutter analyze", "flutter test"],
        "rule": "Flutter-specific structure augments, but does not replace, official Dart/Flutter analyzer and MCP evidence.",
    }
