from __future__ import annotations

from pathlib import Path
from typing import Any

from .util import iter_source_files, safe_rel, tokenize
from .memory import query_learnings


def context_for_task(root: Path, task: str, limit: int = 12) -> dict[str, Any]:
    root = root.resolve()
    q = tokenize(task)
    scored: list[tuple[float, Path, list[str]]] = []

    for p in iter_source_files(root):
        rel = safe_rel(p, root)
        rel_tokens = tokenize(rel.replace("/", " "))
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")[:100_000]
        except OSError:
            continue
        content_tokens = tokenize(text[:20_000])
        path_overlap = q & rel_tokens
        content_overlap = q & content_tokens
        score = 4 * len(path_overlap) + len(content_overlap)
        reasons = []
        if path_overlap:
            reasons.append("path:" + ",".join(sorted(path_overlap)))
        if content_overlap:
            reasons.append("content:" + ",".join(sorted(content_overlap)[:6]))
        if p.name in {"PROJECT_RULES.md", "AGENTS.md", "CLAUDE.md"}:
            score += 3
            reasons.append("policy")
        if "test" in p.parts or p.name.endswith("_test.dart"):
            if content_overlap or path_overlap:
                score += 2
                reasons.append("test")
        if score > 0:
            scored.append((score, p, reasons))

    scored.sort(key=lambda x: (-x[0], safe_rel(x[1], root)))
    chosen = scored[:max(1, min(limit, 30))]
    learnings = query_learnings(root, sorted(q), limit=5)
    return {
        "task": task,
        "query_terms": sorted(q),
        "relevant_learnings": learnings,
        "files": [
            {"path": safe_rel(p, root), "score": round(score, 2), "why": reasons}
            for score, p, reasons in chosen
        ],
        "context_policy": "Read these first; expand only when evidence shows a dependency/caller outside this set.",
    }
