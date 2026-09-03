# Orchestration Kernel

Task states: DEFINED → READY → IMPLEMENTING → VERIFYING → REVIEWING → MERGEABLE → MERGED, with REPAIRING and BLOCKED branches.

Transitions are explicit. Dependencies must be merged before READY. MERGEABLE requires proof_status=pass and zero blocker reviews. Concurrent implementation should use Git worktrees and exclusive ownership.

The model proposes; the kernel records and enforces state.
