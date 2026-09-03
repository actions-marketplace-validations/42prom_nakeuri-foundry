# Full Lifecycle Contract

Foundry manages the engineering lifecycle as an evidence-gated state machine:

Idea → Product definition → Requirements → Project Genome → Architecture → Capability composition → Task DAG → isolated worktrees → implementation → deterministic quality gates → independent logic/simplicity/security/test review → PR/CI → E2E/device assurance → release candidate → staged delivery → observability → learning.

## Non-negotiable gates
- Search canonical capabilities before creating new functionality.
- Declare Change Intent before implementation.
- High-risk invariants have tests.
- Writer cannot be final approver.
- Security HIGH/BLOCKER vetoes merge.
- Mergeable requires a valid proof bound to current HEAD.
- 100 score requires evidence in every weighted domain; compilation is not functional correctness.
