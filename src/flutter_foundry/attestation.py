from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def release_attestation_contract() -> dict[str, Any]:
    return {
        "schema": "nakeuri/release-attestation-contract/v1",
        "slsa": {"version": "1.2", "minimum_build_level": "L2", "target": "L3-capable"},
        "required": [
            "artifact_sha256",
            "source_commit",
            "builder_identity",
            "provenance_verified",
            "sbom_sha256",
            "signature_verified",
            "transparency_or_external_anchor",
        ],
        "preferred": {
            "github": "artifact attestations with OIDC provenance where plan/repository supports it",
            "portable": "Sigstore/Cosign keyless signing with transparency-log verification",
        },
        "rule": "A local checksum alone proves integrity of bytes in hand, not builder identity or provenance.",
    }


def validate_release_attestation(data: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    artifact = str(data.get("artifact_sha256", "")).lower()
    sbom = str(data.get("sbom_sha256", "")).lower()
    commit = str(data.get("source_commit", "")).lower()
    if not _SHA256.fullmatch(artifact):
        findings.append({"severity": "blocker", "issue": "artifact_sha256 missing/invalid"})
    if not _SHA256.fullmatch(sbom):
        findings.append({"severity": "blocker", "issue": "sbom_sha256 missing/invalid"})
    if not _FULL_SHA.fullmatch(commit):
        findings.append({"severity": "blocker", "issue": "source_commit must be full 40-char git SHA"})
    if not str(data.get("builder_identity", "")).strip():
        findings.append({"severity": "blocker", "issue": "builder_identity missing"})
    for field in ("provenance_verified", "signature_verified"):
        if data.get(field) is not True:
            findings.append({"severity": "blocker", "issue": f"{field} not proven"})
    if not (data.get("transparency_log_verified") is True or data.get("external_anchor_verified") is True):
        findings.append({"severity": "blocker", "issue": "no external transparency/anchor verification"})
    if str(data.get("slsa_build_level", "")) not in {"L2", "L3"}:
        findings.append({"severity": "high", "issue": "SLSA Build L2+ not demonstrated"})
    return {
        "status": "fail" if any(f["severity"] == "blocker" for f in findings) else "warn" if findings else "pass",
        "findings": findings,
        "contract": release_attestation_contract(),
    }


def write_attestation_stub(root: Path, artifact: Path, source_commit: str) -> Path:
    root = root.resolve(); artifact = artifact.resolve()
    out = root / ".factory" / "evidence" / "supply-chain" / f"{artifact.name}.attestation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "nakeuri/release-attestation/v1",
        "artifact": str(artifact),
        "artifact_sha256": sha256_file(artifact) if artifact.exists() else None,
        "source_commit": source_commit,
        "builder_identity": None,
        "provenance_verified": False,
        "sbom_sha256": None,
        "signature_verified": False,
        "transparency_log_verified": False,
        "external_anchor_verified": False,
        "slsa_build_level": None,
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out
