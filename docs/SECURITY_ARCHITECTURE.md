# Security Architecture

## Goal

High-assurance, defense-in-depth software development. "Military grade" is intentionally avoided because it is not a precise software assurance standard.

## Trust boundaries

1. User instruction
2. Project-local policy
3. Foundry control plane
4. Agent/model output
5. External web/repository/tool content (untrusted)
6. Production credentials and signing keys (outside normal agent reach)

## Agent least privilege

- explorers: read/search only;
- planners: read + plan artifacts, no source mutation;
- workers: assigned worktree, no `main`, no production secrets;
- security reviewers: scan/review, no feature implementation approval;
- merge/release: consume evidence, human approval for high-risk paths.

## Hook firewall

The Antigravity PreToolUse hook:

- denies clearly destructive shell patterns;
- force-prompts for direct pushes, deploy/publish/signing actions, secret files, and dangerous Git cleanup;
- allows routine deterministic checks.

The hook is a last-mile guardrail, not the sole security boundary.

## Built-in deterministic scan

The lightweight deterministic scanner checks for:

- common secret/token patterns;
- accidental `.env` tracking candidates;
- obvious cleartext production HTTP endpoints;
- Android `allowBackup=true`;
- debug logging of secret-like values;
- dangerous certificate-validation bypass markers.

It is intentionally conservative and does not claim to replace Semgrep, MobSF, Trivy, ZAP, or professional penetration testing.

## Curated external security skills

`registry/security/skill_allowlist.json` defines a small defensive subset from `mukul975/Anthropic-Cybersecurity-Skills`.

Rules:

- never execute upstream `main` directly;
- pin an exact reviewed commit;
- vendor only allowlisted skills;
- record hashes in a lock file;
- offensive/red-team skills are not part of the default worker context;
- red-team execution is permitted only against systems the user owns or is explicitly authorized to test.

Use `scripts/vendor_security_skills.py --commit <sha>` to create a reviewed local snapshot.

## Standards orientation

The Foundry uses OWASP MASVS/MASTG as the mobile-app review vocabulary, NIST SSDF as a secure-development reference, and SLSA concepts for provenance/supply-chain integrity. These are reference frameworks; certification/compliance is a separate activity.
