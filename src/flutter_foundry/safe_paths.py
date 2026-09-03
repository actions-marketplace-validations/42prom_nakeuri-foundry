from __future__ import annotations

import re
from pathlib import Path

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


def safe_identifier(value: str, *, label: str = "identifier") -> str:
    value = str(value)
    if not _ID.fullmatch(value):
        raise ValueError(f"unsafe {label}: {value!r}")
    return value


def resolve_inside(root: Path, value: str | Path, *, must_exist: bool = False) -> Path:
    """Resolve a repository-local path and reject traversal/symlink escapes.

    Absolute inputs are rejected intentionally: evidence/review/proof artifacts are
    portable repository-relative references and must never be able to read arbitrary
    host files.
    """
    root = root.resolve()
    p = Path(value)
    if p.is_absolute():
        raise ValueError("absolute path is not allowed")
    candidate = (root / p).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escapes repository root") from exc
    if must_exist and not candidate.exists():
        raise ValueError("path does not exist")
    return candidate


def relative_inside(root: Path, path: Path) -> str:
    root = root.resolve()
    resolved = path.resolve(strict=False)
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("path escapes repository root") from exc
