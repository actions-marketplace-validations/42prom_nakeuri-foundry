# Security — Nakeuri Foundry

**Build metadata:** `5.0.0a1`

Nakeuri Foundry uses a zero-trust agent/content model. Models, repository content, dependency metadata, web content and MCP output are untrusted until validated by policy and deterministic/runtime evidence.

## Core security rules

- **No raw production secrets in normal model context.** Use protected environments, OIDC or scoped secret stores at privileged executors.
- **Agents do not own unrestricted side effects.** Privileged actions must pass policy and approval gates.
- **Writer ≠ approver.** HIGH/RELEASE work requires independent verification.
- **Risk is monotonic.** Compiler/policy-detected risk can escalate caller input, never be silently downgraded by it.
- **Worktree ≠ security sandbox.** HIGH/RELEASE work requires stronger isolation or an explicit human exception.
- **Provider self-report ≠ proof.** Controller-observed proof obligations are required where the controller can independently verify them.
- **MCP does not bypass lifecycle policy.** MCP lifecycle execution routes through the same provider/risk controls as CLI execution.
- **Stale execution is fenced.** Reclaimed scheduler work uses fencing tokens so an old worker cannot later finalize the task.
- **Source state must be bound.** Proof and release evidence are tied to the exact source state being approved.

## Threat boundaries

Untrusted content may attempt to:

- inject instructions through repository files or web/MCP responses;
- exfiltrate secrets;
- request broader filesystem/network/tool permissions;
- downgrade risk;
- bypass verification through a different entrypoint;
- fabricate runtime evidence;
- reuse stale proof after source drift.

Foundry's architecture addresses these through tool/permission allowlists, bounded network/secret policy, risk escalation, unified lifecycle routing, evidence validation, source fingerprints and independent review.

## Runtime isolation

The runtime policy can require:

- non-root containers;
- read-only root filesystems;
- dropped Linux capabilities;
- `no-new-privileges` / privilege-escalation denial;
- resource limits;
- explicit network policy;
- isolated ephemeral workspace;
- source initialization bound to an exact commit;
- no automatically mounted Kubernetes service-account token where unnecessary.

## Supply chain / release posture

Release assurance is designed to incorporate real tools for:

- SAST;
- SCA/dependency scanning;
- secret scanning;
- container/IaC scanning;
- SBOM generation;
- provenance;
- signing/attestation;
- transparency anchoring;
- staged rollout and rollback evidence.

The repository models these obligations, but full operational proof requires executing the actual toolchain in a release environment.

## Reporting a vulnerability

Please use GitHub private vulnerability reporting / Security Advisories when the repository is published, or contact the project maintainer privately. Do not publish exploit details before a fix is available.

See `docs/SECURITY_ARCHITECTURE.md`, `docs/MCP_SECURITY_GATEWAY.md` and `docs/EVIDENCE_LEDGER.md`.
