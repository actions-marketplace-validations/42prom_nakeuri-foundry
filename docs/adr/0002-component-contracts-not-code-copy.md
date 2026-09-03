# ADR-0002: Component contracts over code-copy templates

Status: Accepted

## Decision

Reusable "puzzle pieces" are capability contracts first. A capsule specifies dependencies, conflicts, risk, acceptance criteria, and verification. It may later provide an implementation template, but the contract remains the stable interface.

## Why

Blindly copying auth/payment/offline folders creates hidden coupling and stale dependencies. Capability contracts let an agent adapt implementation to the project's current architecture while preserving measurable outcomes.
