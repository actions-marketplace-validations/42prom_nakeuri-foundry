from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StandardRecord:
    id: str
    authority: str
    category: str
    version: str
    status: str
    source: str
    checked_at: str
    review_days: int
    ring: str = "ADOPT"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# This registry is intentionally source/version/status aware. It is a checked snapshot,
# not a claim that the internet can be queried from every Foundry installation.
DEFAULT_STANDARDS: tuple[StandardRecord, ...] = (
    StandardRecord(
        id="flutter.ai-stack",
        authority="Flutter team",
        category="flutter",
        version="Flutter 3.47.2 docs snapshot",
        status="stable",
        source="https://docs.flutter.dev/ai/get-started",
        checked_at="2026-09-03",
        review_days=30,
        notes="Official Agent Skills + Dart/Flutter MCP; Developer Knowledge MCP and package skills are complementary.",
    ),
    StandardRecord(
        id="mcp.spec",
        authority="Model Context Protocol maintainers",
        category="agent-protocol",
        version="2026-07-28",
        status="stable",
        source="https://blog.modelcontextprotocol.io/posts/2026-07-28/",
        checked_at="2026-09-02",
        review_days=30,
        notes="Stateless core, Tasks extension, authorization hardening; legacy HTTP+SSE and Roots/Sampling/Logging deprecated.",
    ),
    StandardRecord(
        id="slsa",
        authority="SLSA",
        category="supply-chain",
        version="1.2",
        status="approved",
        source="https://slsa.dev/spec/v1.2/provenance",
        checked_at="2026-09-02",
        review_days=90,
    ),
    StandardRecord(
        id="github.artifact-attestations",
        authority="GitHub",
        category="supply-chain",
        version="current docs",
        status="stable",
        source="https://docs.github.com/en/actions/concepts/security/artifact-attestations",
        checked_at="2026-09-02",
        review_days=30,
    ),
    StandardRecord(
        id="opentelemetry.semconv",
        authority="OpenTelemetry",
        category="observability",
        version="1.44.0",
        status="mixed-stability",
        source="https://opentelemetry.io/docs/specs/semconv/",
        checked_at="2026-09-02",
        review_days=30,
        ring="TRIAL",
        notes="Use stable conventions by default; experimental/development conventions require explicit opt-in and version pinning.",
    ),
    StandardRecord(
        id="owasp.asvs",
        authority="OWASP",
        category="web-api-security",
        version="5.0.0",
        status="stable",
        source="https://owasp.org/www-project-application-security-verification-standard/",
        checked_at="2026-09-02",
        review_days=90,
        notes="Use risk-appropriate ASVS verification; do not convert the entire standard into mandatory checks for trivial components.",
    ),
    StandardRecord(
        id="owasp.masvs",
        authority="OWASP",
        category="mobile-security",
        version="current MASVS/MASTG/MASWE",
        status="stable",
        source="https://mas.owasp.org/MASVS/",
        checked_at="2026-09-02",
        review_days=90,
        notes="Industry-standard mobile verification baseline with MASTG/MASWE companions.",
    ),
    StandardRecord(
        id="nist.ssdf",
        authority="NIST",
        category="secure-development",
        version="SP 800-218 v1.1",
        status="final",
        source="https://csrc.nist.gov/pubs/sp/800/218/final",
        checked_at="2026-09-02",
        review_days=90,
        notes="Final normative baseline; newer drafts remain assessment/watchlist material until final.",
    ),
    StandardRecord(
        id="sigstore.keyless",
        authority="Sigstore",
        category="supply-chain",
        version="current docs",
        status="stable",
        source="https://docs.sigstore.dev/cosign/signing/overview/",
        checked_at="2026-09-02",
        review_days=60,
        notes="Prefer OIDC/keyless signing and transparency-log verification where the release environment supports it.",
    ),
    StandardRecord(
        id="opentelemetry.declarative-config",
        authority="OpenTelemetry",
        category="observability",
        version="configuration schema 1.0.0",
        status="stable",
        source="https://opentelemetry.io/blog/2026/stable-declarative-config/",
        checked_at="2026-09-02",
        review_days=60,
        notes="Use vendor-neutral declarative telemetry configuration where SDK support is stable.",
    ),
)


def _parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def init_standards_radar(root: Path, force: bool = False) -> Path:
    root = root.resolve()
    directory = root / ".factory" / "standards"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "registry.json"
    if path.exists() and not force:
        return path
    payload = {
        "schema": "nakeuri/standards-registry/v1",
        "policy": {
            "prefer_proven_over_newest": True,
            "require_source": True,
            "require_version_or_snapshot": True,
            "drafts_are_not_normative": True,
            "rings": ["ADOPT", "TRIAL", "ASSESS", "HOLD"],
        },
        "records": [x.to_dict() for x in DEFAULT_STANDARDS],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def standards_status(root: Path, *, now: datetime | None = None) -> dict[str, Any]:
    path = root.resolve() / ".factory" / "standards" / "registry.json"
    if not path.exists():
        return {"status": "fail", "reason": "standards registry missing", "path": str(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "fail", "reason": f"invalid standards registry: {exc}", "path": str(path)}
    if data.get("schema") != "nakeuri/standards-registry/v1":
        return {"status": "fail", "reason": "unsupported standards registry schema", "path": str(path)}
    now = now or datetime.now(timezone.utc)
    findings: list[dict[str, Any]] = []
    records = data.get("records", [])
    for rec in records:
        rid = str(rec.get("id", ""))
        for required in ("authority", "category", "version", "status", "source", "checked_at", "review_days", "ring"):
            if rec.get(required) in {None, ""}:
                findings.append({"id": rid, "severity": "high", "issue": f"missing {required}"})
        try:
            age = (now - _parse_date(str(rec["checked_at"]))).days
            if age > int(rec["review_days"]):
                findings.append({"id": rid, "severity": "medium", "issue": "source snapshot is stale", "age_days": age})
        except Exception:
            findings.append({"id": rid, "severity": "high", "issue": "invalid freshness metadata"})
        if str(rec.get("status", "")).lower() in {"draft", "experimental"} and rec.get("ring") == "ADOPT":
            findings.append({"id": rid, "severity": "high", "issue": "draft/experimental standard cannot be ADOPT by default"})
    high = sum(1 for f in findings if f["severity"] == "high")
    medium = sum(1 for f in findings if f["severity"] == "medium")
    return {
        "status": "fail" if high else "warn" if medium else "pass",
        "schema": data["schema"],
        "records": len(records),
        "findings": findings,
        "path": str(path),
        "rule": "Freshness informs decisions; newest is not automatically best. Only supported, compatible and justified practices are adopted.",
    }


def technology_radar(root: Path) -> dict[str, list[dict[str, Any]]]:
    path = root.resolve() / ".factory" / "standards" / "registry.json"
    if not path.exists():
        init_standards_radar(root)
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[dict[str, Any]]] = {"ADOPT": [], "TRIAL": [], "ASSESS": [], "HOLD": []}
    for rec in data.get("records", []):
        ring = rec.get("ring", "ASSESS")
        out.setdefault(ring, []).append(rec)
    return out
