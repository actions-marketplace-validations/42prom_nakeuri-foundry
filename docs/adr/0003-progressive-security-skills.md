# ADR-0003: Progressive security skill loading

Status: Accepted

## Decision

Do not load a giant cybersecurity catalog into every task. Keep a reviewed defensive allowlist, pin an exact upstream commit before vendoring, and load specialized/red-team material only for an authorized security workflow.

## Consequences

- lower context cost;
- smaller prompt-injection/supply-chain surface;
- easier review of what security knowledge can influence a task.
