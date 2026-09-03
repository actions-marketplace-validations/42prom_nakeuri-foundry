# Execution Fabric

Execution providers are interchangeable contracts: local worktree, Docker, OpenHands, remote ephemeral, Kubernetes and CI runners.

Risk routing does not confuse convenience with isolation. Worktree is fast local isolation, not a security sandbox. HIGH/RELEASE workloads target container/remote/controlled-CI execution or require a recorded exception.

Privileged actions pass through a side-effect firewall. Production secrets follow a short-lived scoped credential policy and are not model input.
