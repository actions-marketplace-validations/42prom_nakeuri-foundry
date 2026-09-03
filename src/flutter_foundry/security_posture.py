from __future__ import annotations

import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .platform_adapters import detect_project_surfaces


@dataclass(frozen=True)
class SecurityTool:
    id: str
    command: str
    purpose: str
    required_for_release: bool
    applies_to: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["applies_to"] = list(self.applies_to)
        d["available"] = shutil.which(self.command) is not None
        return d


TOOLS: tuple[SecurityTool, ...] = (
    SecurityTool("gitleaks", "gitleaks", "secrets scanning", True),
    SecurityTool("osv-scanner", "osv-scanner", "known dependency vulnerabilities", True),
    SecurityTool("semgrep", "semgrep", "multi-language SAST", True),
    SecurityTool("trivy", "trivy", "filesystem/container/IaC vulnerability scanning", True),
    SecurityTool("syft", "syft", "SBOM generation", True),
    SecurityTool("grype", "grype", "SBOM/container vulnerability analysis", False),
    SecurityTool("checkov", "checkov", "IaC policy scanning", False),
    SecurityTool("zizmor", "zizmor", "GitHub Actions security analysis", False),
    SecurityTool("actionlint", "actionlint", "GitHub Actions correctness", False),
    SecurityTool("cosign", "cosign", "keyless signing and attestation verification", True),
    SecurityTool("docker", "docker", "container image/runtime security evidence", False),
    SecurityTool("flutter", "flutter", "mobile build/runtime verification", False, ("flutter",)),
)


SECURITY_STANDARDS = {
    "web_api": {"standard": "OWASP ASVS", "version": "5.0.0", "level_target": "L2 baseline; L3 for high-assurance components"},
    "mobile": {"standard": "OWASP MASVS", "companion": "MASTG/MASWE", "level_target": "risk-appropriate control verification"},
    "secure_development": {"standard": "NIST SSDF", "version": "1.1 final", "level_target": "project-tailored practices"},
    "supply_chain": {"standard": "SLSA", "version": "1.2 approved", "level_target": "Build L2 minimum, L3-capable release path"},
    "signing": {"standard": "Sigstore/Cosign", "mode": "OIDC keyless where supported", "transparency": "Rekor"},
}


def security_posture(root: Path, *, release: bool = False) -> dict[str, Any]:
    root = root.resolve()
    surfaces = detect_project_surfaces(root)
    ids = {s["id"] for s in surfaces}
    tool_rows = [t.to_dict() for t in TOOLS]
    required = []
    missing_required = []
    for tool in tool_rows:
        applicable = not tool["applies_to"] or bool(ids.intersection(tool["applies_to"]))
        tool["applicable"] = applicable
        if release and tool["required_for_release"] and applicable:
            required.append(tool["id"])
            if not tool["available"]:
                missing_required.append(tool["id"])
    controls = {
        "source": ["SAST", "secrets", "dependency/SCA", "license review"],
        "mobile": ["MASVS", "permissions", "secure storage", "TLS", "deep links", "platform config"] if "flutter" in ids else [],
        "web_api": ["ASVS", "auth/session", "RBAC/tenant isolation", "input/output validation", "rate limits"] if ids.intersection({"node", "nextjs", "python", "dotnet", "go", "java"}) else [],
        "supply_chain": ["lockfiles", "immutable CI action refs", "SBOM", "provenance", "keyless signing", "attestation verification"],
        "agent": ["sandbox", "MCP allowlists", "prompt-injection boundary", "secret broker", "network policy", "side-effect firewall"],
    }
    return {
        "status": "pass_with_gaps" if missing_required else "pass",
        "schema": "nakeuri/security-posture/v1",
        "release": release,
        "surfaces": surfaces,
        "standards": SECURITY_STANDARDS,
        "controls": controls,
        "tools": tool_rows,
        "required_tools": required,
        "missing_required_tools": missing_required,
        "rule": "Missing external scanners/signers are explicit release evidence gaps; architecture presence never substitutes for their execution.",
    }
