from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any


@dataclass
class CheckResult:
    name: str
    status: str
    command: str | None = None
    returncode: int | None = None
    duration_ms: int | None = None
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RiskResult:
    level: str
    score: int
    reasons: list[str] = field(default_factory=list)
    execution: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
