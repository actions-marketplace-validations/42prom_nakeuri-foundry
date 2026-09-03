from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .safe_paths import safe_identifier


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, timeout=30)


def status(root: Path) -> dict[str, Any]:
    root = root.resolve()
    head = _run(root, "rev-parse", "HEAD")
    branch = _run(root, "branch", "--show-current")
    dirty = _run(root, "status", "--porcelain")
    return {
        "git": head.returncode == 0,
        "commit": head.stdout.strip() if head.returncode == 0 else None,
        "branch": branch.stdout.strip() if branch.returncode == 0 else None,
        "dirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else None,
        "changes": dirty.stdout.splitlines() if dirty.returncode == 0 else [],
    }


def require_clean(root: Path) -> dict[str, Any]:
    s = status(root)
    if not s["git"]: return {"status": "fail", "reason": "not a git repository", **s}
    if s["dirty"]: return {"status": "fail", "reason": "source worktree is dirty", **s}
    return {"status": "pass", **s}


def create_isolated_worktree(root: Path, task_id: str, branch: str | None = None) -> dict[str, Any]:
    task_id = safe_identifier(task_id, label="task_id")
    root = root.resolve(); clean = require_clean(root)
    if clean["status"] != "pass": return clean
    branch = branch or f"feat/{task_id.lower()}"
    valid_branch = _run(root, "check-ref-format", "--branch", branch)
    if valid_branch.returncode != 0:
        return {"status": "fail", "reason": "unsafe/invalid git branch name"}
    target = root / ".factory" / "worktrees" / task_id.lower()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists(): return {"status": "fail", "reason": f"worktree path already exists: {target}"}
    p = _run(root, "worktree", "add", "-b", branch, str(target), "HEAD")
    if p.returncode != 0: return {"status": "fail", "reason": (p.stderr or p.stdout).strip()[-4000:]}
    return {"status": "pass", "worktree": str(target), "branch": branch, "base_commit": clean["commit"]}


def require_worker_commit(worktree: Path, base_commit: str) -> dict[str, Any]:
    s = status(worktree)
    if not s["git"]: return {"status": "fail", "reason": "task worktree is not git-backed"}
    if s["dirty"]: return {"status": "fail", "reason": "worker left uncommitted changes", **s}
    if s["commit"] == base_commit: return {"status": "fail", "reason": "worker produced no commit", **s}
    diff = _run(worktree, "diff", "--name-only", f"{base_commit}..HEAD")
    files = [x for x in diff.stdout.splitlines() if x.strip()] if diff.returncode == 0 else []
    return {"status": "pass", "commit": s["commit"], "branch": s["branch"], "changed_files": files}
