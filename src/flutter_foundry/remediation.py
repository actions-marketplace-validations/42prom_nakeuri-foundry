from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RemediationAction:
    category: str
    target_file: str
    description: str
    action_type: str  # create, replace, format
    applied: bool


def scan_and_remediate(root: Path, *, apply: bool = True) -> dict[str, Any]:
    """Surgical auto-remediation engine for governance, manifests, and git configurations."""
    root = root.resolve()
    actions: list[RemediationAction] = []

    # 1. Check for standard .gitignore hygiene in mobile/polyglot roots
    gitignore = root / ".gitignore"
    if gitignore.exists():
        try:
            content = gitignore.read_text(encoding="utf-8")
            missing = [line for line in [".nakeuri/cache", ".foundry/cache", "*.pyc", "__pycache__/"] if line not in content]
            if missing:
                if apply:
                    with gitignore.open("a", encoding="utf-8") as f:
                        f.write("\n# Nakeuri Foundry internal cache\n" + "\n".join(missing) + "\n")
                actions.append(RemediationAction(
                    category="hygiene",
                    target_file=".gitignore",
                    description=f"Add missing cache ignore rules: {', '.join(missing)}",
                    action_type="append",
                    applied=apply,
                ))
        except Exception:
            pass

    # 2. Check for missing durable evidence directory
    evidence_dir = root / ".foundry" / "evidence"
    if not evidence_dir.exists():
        if apply:
            evidence_dir.mkdir(parents=True, exist_ok=True)
        actions.append(RemediationAction(
            category="governance",
            target_file=".foundry/evidence",
            description="Initialize missing durable evidence storage directory",
            action_type="mkdir",
            applied=apply,
        ))

    return {
        "schema": "nakeuri/auto-remediation/v1",
        "status": "remediated" if any(a.applied for a in actions) else "clean",
        "actions_found": len(actions),
        "actions": [asdict(a) for a in actions],
        "rule": "Surgical auto-remediation produces minimal, verifiable state fixes without human override of strict security boundaries.",
    }
