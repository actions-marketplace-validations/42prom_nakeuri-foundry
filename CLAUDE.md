# Compatibility Behavior Layer

Use only task-relevant skills. Project-local rules override generic skill defaults.

Before editing:
- clarify only genuinely blocking ambiguity;
- identify the smallest change that can satisfy the requirement;
- define success in executable terms;
- assess blast radius.

While editing:
- touch only in-scope code;
- match local conventions;
- keep business logic testable outside Flutter widgets;
- avoid speculative scalability and generic Base* abstractions.

After editing:
- re-read changed files;
- run the failing/targeted test first;
- run the required Foundry verification profile;
- generate or update proof evidence;
- do not infer success from prose or memory.
