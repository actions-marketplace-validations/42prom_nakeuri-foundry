# V3 Universal Foundry Architecture

V3 separates a universal **Nakeuri Engineering Foundry Core** from deep platform adapters. Flutter is the flagship profile, not a limitation of the core.

```text
Product + Standards + Genome
            ↓
Software Knowledge Graph
            ↓
Governance / Security / Invariants
            ↓
Durable Orchestration + Execution Fabric
            ↓
Flutter | Next.js | Node | Python | .NET | Go | Rust | Java
            ↓
Assurance → Evidence → Delivery → Production → Learning
```

Key design constraint: **one control plane, many adapters/providers**. OpenHands may be one execution provider; it is not allowed to become a second governance truth. Official framework tooling remains the semantic authority for each adapter.
