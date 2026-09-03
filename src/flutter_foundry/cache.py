from __future__ import annotations

import concurrent.futures
import hashlib
import json
from pathlib import Path
from typing import Any, Callable


class FoundryCache:
    """High-performance fingerprint-aware cache for Foundry static scans."""

    def __init__(self, root: Path, cache_dir_name: str = ".nakeuri/cache") -> None:
        self.root = root.resolve()
        self.cache_dir = self.root / cache_dir_name

    def _ensure_cache_dir(self) -> Path:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        return self.cache_dir

    def _cache_key(self, namespace: str, target_path: Path) -> str:
        rel = target_path.resolve().relative_to(self.root).as_posix() if target_path.resolve() != self.root else "."
        h = hashlib.sha256(f"{namespace}:{rel}".encode("utf-8")).hexdigest()[:16]
        return f"{namespace}_{h}.json"

    def get(self, namespace: str, target_path: Path, current_fingerprint: str) -> dict[str, Any] | None:
        target_file = self.cache_dir / self._cache_key(namespace, target_path)
        if not target_file.exists():
            return None
        try:
            data = json.loads(target_file.read_text(encoding="utf-8"))
            if data.get("fingerprint") == current_fingerprint:
                return data.get("payload")
        except Exception:
            return None
        return None

    def set(self, namespace: str, target_path: Path, current_fingerprint: str, payload: dict[str, Any]) -> None:
        try:
            self._ensure_cache_dir()
            target_file = self.cache_dir / self._cache_key(namespace, target_path)
            data = {
                "schema": "nakeuri/cache-entry/v1",
                "namespace": namespace,
                "fingerprint": current_fingerprint,
                "payload": payload,
            }
            target_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass


def parallel_map(fn: Callable[[Any], Any], items: list[Any], max_workers: int = 4) -> list[Any]:
    """Execute read-only diagnostic functions concurrently across subpaths/surfaces."""
    if not items:
        return []
    if len(items) == 1:
        return [fn(items[0])]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as executor:
        return list(executor.map(fn, items))
