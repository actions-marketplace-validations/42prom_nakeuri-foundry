from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .util import iter_source_files, safe_rel

SECRET_PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("generic-api-key", re.compile(r"(?i)(?:api[_-]?key|secret|token)\s*[:=]\s*['\"]([A-Za-z0-9_\-]{20,})['\"]")),
    ("aws-access-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github-token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{30,}")),
]

DANGEROUS_PATTERNS = [
    ("cleartext-production-url", re.compile(r"http://(?!localhost|127\.0\.0\.1|10\.0\.2\.2)[A-Za-z0-9.-]+", re.I)),
    ("android-backup-enabled", re.compile(r"android:allowBackup\s*=\s*[\"']true[\"']", re.I)),
    ("tls-validation-bypass", re.compile(r"badCertificateCallback\s*=|onBadCertificate\s*=", re.I)),
    ("secret-log", re.compile(r"(?i)(?:print|debugPrint|log)\s*\([^\n]*(?:token|password|secret|authorization)")),
]


def scan_project(root: Path, max_file_bytes: int = 500_000) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    for p in iter_source_files(root):
        try:
            if p.stat().st_size > max_file_bytes:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = safe_rel(p, root)
        for rule, pattern in SECRET_PATTERNS + DANGEROUS_PATTERNS:
            for m in pattern.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                findings.append({"rule": rule, "severity": "high" if rule in {"private-key","generic-api-key","aws-access-key","github-token","tls-validation-bypass"} else "medium", "path": rel, "line": line})
                if len(findings) >= 200:
                    break
            if len(findings) >= 200:
                break
        if len(findings) >= 200:
            break

    env_files = [p for p in root.rglob(".env*") if p.is_file() and ".git" not in p.parts]
    for p in env_files[:20]:
        if p.name not in {".env.example", ".env.sample"}:
            findings.append({"rule":"env-file-present","severity":"medium","path":safe_rel(p, root),"line":1})

    high = sum(1 for f in findings if f["severity"] == "high")
    medium = sum(1 for f in findings if f["severity"] == "medium")
    return {
        "status": "fail" if high else "warn" if medium else "pass",
        "summary": {"high": high, "medium": medium, "total": len(findings)},
        "findings": findings,
        "scope": "lightweight deterministic scan; run dedicated SAST/SCA/mobile security tools for release assurance"
    }
