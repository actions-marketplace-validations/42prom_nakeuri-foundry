# ADR-0001: Evidence-first control plane

Status: Accepted

## Decision

The Foundry will not use LLM consensus as its correctness oracle. Deterministic evidence is authoritative wherever a machine-checkable contract exists. Model review is used for ambiguity, architecture, adversarial reasoning, and gaps that deterministic tools cannot decide.

## Consequences

- lower token/model spend for routine work;
- more reproducible completion decisions;
- some quality dimensions remain explicitly "unproven" until runtime/device evidence exists;
- the system prefers honest gaps over synthetic confidence.
