# Cost Model

The Foundry optimizes **total engineering cost**, not raw token count.

## Cheap by default

Use deterministic tools for deterministic questions:

- format
- compile/analyze
- symbol/call-site search
- test execution
- dependency graph
- policy checks
- secret scanning
- Git diff/statistics

## Model tiers

The router returns abstract tiers so the project can map them to Gemini, Claude, Codex, local models, or future providers.

- `economy`: classification, routine edits, summaries, simple reviews
- `balanced`: feature implementation and moderate reasoning
- `flagship`: architecture ambiguity, security-sensitive design, repeated failure, final high-risk review

## Escalation

Do not launch extra agents pre-emptively. Escalate on evidence:

- deterministic gate failure that the worker cannot repair within budget;
- high-risk subsystem;
- ambiguity above configured threshold;
- repeated failure pattern;
- conflicting reviewer evidence.

## Context budget

The default context compiler returns a maximum of 12 files and short excerpts/metadata. Whole-repo reads require explicit justification.
