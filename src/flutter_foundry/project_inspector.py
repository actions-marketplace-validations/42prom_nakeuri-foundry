from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from .util import safe_rel

_DEP_RE = re.compile(r"^\s{2}([a-zA-Z0-9_]+):(?:\s|$)", re.MULTILINE)


def _git(root: Path, *args: str) -> str | None:
    try:
        p = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, timeout=4)
        return p.stdout.strip() if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def inspect_project(root: Path) -> dict[str, Any]:
    root = root.resolve()
    pubspec = root / "pubspec.yaml"
    pub_text = pubspec.read_text(encoding="utf-8", errors="ignore") if pubspec.exists() else ""
    deps = sorted(set(_DEP_RE.findall(pub_text)))

    feature_root_candidates = [root / "lib" / "features", root / "mobile" / "lib" / "features"]
    feature_root = next((p for p in feature_root_candidates if p.exists()), None)
    features = sorted(p.name for p in feature_root.iterdir() if p.is_dir()) if feature_root else []

    lib_root = root / "lib"
    if not lib_root.exists() and (root / "mobile" / "lib").exists():
        lib_root = root / "mobile" / "lib"

    dart_files = list(lib_root.rglob("*.dart")) if lib_root.exists() else []
    test_roots = [p for p in [root / "test", root / "mobile" / "test"] if p.exists()]
    test_files = [f for t in test_roots for f in t.rglob("*_test.dart")]

    rules = root / "PROJECT_RULES.md"
    factory_cfg = root / "factory.json"

    risk_surfaces = []
    joined = " ".join(deps).lower()
    signals = {
        "authentication": ["google_sign_in", "sign_in_with_apple", "firebase_auth"],
        "payments": ["flutter_stripe", "in_app_purchase"],
        "notifications": ["firebase_messaging", "flutter_local_notifications"],
        "secure_storage": ["flutter_secure_storage"],
        "camera": ["camera", "image_picker", "mobile_scanner"],
        "biometrics": ["local_auth"],
        "realtime": ["socket_io_client", "web_socket_channel"],
    }
    for surface, names in signals.items():
        if any(n in joined for n in names):
            risk_surfaces.append(surface)

    return {
        "root": str(root),
        "is_flutter": bool(pubspec.exists() and "flutter:" in pub_text),
        "git_head": _git(root, "rev-parse", "--short", "HEAD"),
        "git_branch": _git(root, "branch", "--show-current"),
        "dirty": bool(_git(root, "status", "--porcelain") or ""),
        "project_rules": safe_rel(rules, root) if rules.exists() else None,
        "factory_config": safe_rel(factory_cfg, root) if factory_cfg.exists() else None,
        "dependencies": deps,
        "features": features,
        "dart_file_count": len(dart_files),
        "test_file_count": len(test_files),
        "risk_surfaces": risk_surfaces,
        "architecture_hints": {
            "feature_first": feature_root is not None,
            "riverpod": any(d in deps for d in ["flutter_riverpod", "riverpod", "riverpod_annotation"]),
            "bloc": any(d in deps for d in ["flutter_bloc", "bloc"]),
            "go_router": "go_router" in deps,
            "dio": "dio" in deps,
        },
    }
