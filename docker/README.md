# Docker execution profile

Foundry provides a first-class hardened Docker execution profile, but the end-to-end lifecycle is not Docker-only and not every lifecycle path is currently wired through Docker. The repository image intentionally has no floating base-image default: release and high-assurance builds must supply `NAKEURI_BASE_IMAGE` as an immutable `@sha256:` reference.

The compose profile runs non-root, read-only, with all Linux capabilities dropped, `no-new-privileges`, bounded PIDs/CPU/memory, a no-exec tmpfs, and no network by default. A task that genuinely needs package/network access should use the Execution Fabric's explicit egress policy rather than weakening the default profile globally.

The requested container policy is not runtime evidence. `DockerExecutor` inspects the created container and validates observed isolation facts before a HIGH/RELEASE task can treat the runtime as proven.
