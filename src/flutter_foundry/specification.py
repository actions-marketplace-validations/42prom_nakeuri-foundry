from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, asdict
from typing import Any

from .component_registry import ComponentRegistry
from .risk_engine import classify_risk

_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
_ACTION = re.compile(r"\b(add|create|build|implement|support|allow|enable|fix|prevent|update|change|remove|delete|migrate|integrate|show|display|send|sync|save|load|scan|track|verify|publish|deploy)\b", re.I)

NFR_HINTS: dict[str, tuple[str, ...]] = {
    "security": ("auth", "login", "password", "token", "payment", "billing", "secret", "permission", "encrypt", "privacy", "admin"),
    "reliability": ("offline", "retry", "realtime", "real-time", "sync", "queue", "background", "notification", "payment", "migration"),
    "performance": ("performance", "fast", "latency", "scroll", "animation", "startup", "large list", "image", "video"),
    "accessibility": ("accessibility", "screen reader", "large text", "responsive", "adaptive", "tablet", "desktop"),
    "observability": ("crash", "monitor", "analytics", "logging", "telemetry", "production"),
}

NEGATIVE_CASES: dict[str, list[str]] = {
    "auth-session": ["invalid or expired credentials fail closed", "another user's session cannot be reused"],
    "payments-boundary": ["duplicate callbacks cannot charge or fulfill twice", "failed/cancelled payment never grants paid entitlement"],
    "offline-outbox": ["replayed queued mutations are idempotent", "conflicts do not silently overwrite newer server state"],
    "push-notifications": ["duplicate delivery is harmless", "revoked notification permission has a non-crashing fallback"],
    "network-dio": ["timeout and server errors produce bounded retries/fallbacks", "malformed API payloads do not corrupt local state"],
    "location": ["denied permission does not block unrelated app flows", "background location is never assumed without explicit authorization"],
    "camera": ["denied camera permission has a safe fallback", "invalid scan payloads are rejected"],
    "in-app-purchase": ["restore/replay is idempotent", "unverified store transactions never unlock entitlement"],
}


def _rid(prefix: str, text: str, index: int) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:6].upper()
    return f"{prefix}-{index:03d}-{digest}"


def _clauses(brief: str) -> list[str]:
    parts: list[str] = []
    for raw in _SENTENCE.split(brief.strip()):
        raw = " ".join(raw.split()).strip(" -\t")
        if not raw:
            continue
        # Split obvious multi-requirement sentences without destroying ordinary prose.
        chunks = re.split(r"\s*[;•]\s*|\s+and also\s+|\s+also\s+", raw, flags=re.I)
        parts.extend(c.strip() for c in chunks if c.strip())
    return parts or [brief.strip()]


def _explicit_requirements(brief: str) -> list[dict[str, Any]]:
    clauses = _clauses(brief)
    selected = [c for c in clauses if _ACTION.search(c)] or clauses
    out=[]
    for i, c in enumerate(selected, 1):
        out.append({
            "id": _rid("REQ", c, i),
            "statement": c,
            "source": "user-brief",
            "inferred": False,
            "acceptance_oracle": {
                "given": "the relevant preconditions and authorized actor are established",
                "when": c,
                "then": "the requested behavior is observable and all affected invariants remain true",
            },
        })
    return out


def _nfrs(text: str) -> list[dict[str, Any]]:
    low = text.lower(); out=[]; idx=1
    defaults={
        "security":"sensitive actions fail closed and preserve authorization/privacy boundaries",
        "reliability":"retries, duplicate events and partial failures do not create inconsistent state",
        "performance":"the changed critical path remains inside the project's declared performance budget",
        "accessibility":"the changed UI remains operable with semantics, large text and supported form factors",
        "observability":"production-impacting failures emit safe diagnostic evidence without secrets or personal data",
    }
    for kind,hints in NFR_HINTS.items():
        if any(h in low for h in hints):
            statement=defaults[kind]
            out.append({"id":_rid("NFR",statement,idx),"kind":kind,"statement":statement,"inferred":True});idx+=1
    return out


def compile_specification(brief: str, *, component_ids: list[str] | None = None) -> dict[str, Any]:
    """Compile a user brief into an auditable, executable-spec hypothesis.

    This compiler deliberately separates user-authored requirements from inferred
    non-functional/negative cases. Inferred items are reviewable hypotheses and never
    silently expand product scope.
    """
    if not brief.strip():
        raise ValueError("brief must not be empty")
    registry=ComponentRegistry()
    components=[]
    if component_ids:
        components=registry.resolve(component_ids).get("components",[])
    reqs=_explicit_requirements(brief)
    nfrs=_nfrs(brief)
    negative=[]; idx=1
    for c in components:
        for case in NEGATIVE_CASES.get(c.get("id",""),[]):
            negative.append({"id":_rid("NEG",case,idx),"component":c["id"],"statement":case,"inferred":True});idx+=1
    component_acceptance=[]; idx=1
    for c in components:
        for criterion in c.get("acceptance",[]):
            component_acceptance.append({"id":_rid("AC",criterion,idx),"component":c["id"],"criterion":criterion,"source":"component-contract"});idx+=1
    risks=[str(c.get("risk","medium")) for c in components]
    risk=classify_risk(brief,component_risks=risks).to_dict()
    oracle_ids=[x["id"] for x in reqs]+[x["id"] for x in component_acceptance]+[x["id"] for x in negative]+[x["id"] for x in nfrs]
    return {
        "schema":"nakeuri/executable-specification/v2",
        "brief":brief,
        "requirements":reqs,
        "component_acceptance":component_acceptance,
        "negative_cases":negative,
        "non_functional_requirements":nfrs,
        "risk":risk,
        "oracle_ids":oracle_ids,
        "coverage_contract":{
            "all_requirement_ids_must_map_to_evidence":True,
            "high_risk_test_oracles_are_independent_from_implementation_worker":True,
            "inferred_items_require_review_before_scope_expansion":True,
        },
        "status":"pass",
    }
