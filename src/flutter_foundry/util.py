from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parents[1]
ASSET_ROOT = PACKAGE_ROOT / "assets"


def json_load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def workspace_path(value: str | Path | None = None) -> Path:
    raw = value or os.getenv("FLUTTER_FOUNDRY_WORKSPACE") or "."
    return Path(raw).expanduser().resolve()


def tokenize(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[A-Za-z0-9_]+", text) if len(t) > 2}


def iter_source_files(root: Path) -> Iterable[Path]:
    ignored = {".git", ".dart_tool", "build", ".idea", ".vscode", "node_modules", ".factory"}
    suffixes = {".dart", ".yaml", ".yml", ".json", ".md", ".kt", ".kts", ".swift", ".m", ".mm", ".plist", ".xml", ".gradle", ".properties"}
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in suffixes:
            continue
        if any(part in ignored for part in p.parts):
            continue
        yield p


def safe_rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
