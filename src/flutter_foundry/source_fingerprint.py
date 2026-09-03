from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

_EXCLUDED_DIRS = {
    ".git", ".factory", ".venv", "build", "dist", ".dist", "__pycache__", ".pytest_cache", ".dart_tool",
}
_EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def _included(root: Path, path: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in _EXCLUDED_DIRS or part.endswith(".egg-info") for part in rel.parts):
        return False
    if path.suffix in _EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def repository_fingerprint(root: Path) -> dict[str, Any]:
    """Hash the versioned/release-relevant repository content deterministically.

    Runtime state (.factory), VCS metadata and generated build/cache outputs are excluded.
    The digest binds certification to the source snapshot that was actually audited.
    """
    root = root.resolve()
    h = hashlib.sha256()
    count = 0
    total_bytes = 0
    for path in sorted((p for p in root.rglob("*") if _included(root, p)), key=lambda p: p.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        file_hash = hashlib.sha256(data).digest()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(file_hash)
        count += 1
        total_bytes += len(data)
    return {
        "schema": "nakeuri/repository-fingerprint/v1",
        "algorithm": "sha256(path-length || path || size || sha256(file))",
        "sha256": h.hexdigest(),
        "files": count,
        "bytes": total_bytes,
        "excluded": sorted(_EXCLUDED_DIRS),
    }
