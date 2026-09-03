from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .util import iter_source_files, safe_rel
from .semantic_snapshot import symbol_impact


def blast_radius(root: Path, symbol: str, max_matches: int = 200) -> dict[str, Any]:
    root = root.resolve()
    semantic = symbol_impact(root, symbol)
    if semantic is not None:
        return semantic
    pattern = re.compile(rf"\b{re.escape(symbol)}\b")
    matches: list[dict[str, Any]] = []
    for p in iter_source_files(root):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        count = len(pattern.findall(text))
        if count:
            matches.append({"path": safe_rel(p, root), "occurrences": count})
            if len(matches) >= max_matches:
                break
    files = len(matches)
    occ = sum(m["occurrences"] for m in matches)
    level = "safe" if files <= 3 else "caution" if files <= 10 else "risk"
    return {"symbol": symbol, "files": files, "occurrences": occ, "level": level, "matches": matches}
