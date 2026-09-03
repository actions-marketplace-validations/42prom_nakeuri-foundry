# Contributing

The Foundry optimizes for small, measurable improvements.

1. Open a focused issue/brief.
2. Work on a non-main branch.
3. Add a test for new deterministic behavior.
4. Run `python -m unittest discover -s tests -v`.
5. Avoid framework additions unless benchmark evidence shows a real gap.
6. New component capsules must define provides/requires/conflicts/risk/acceptance/verification.
7. Security tooling must fail honestly when unavailable; never report a scan as passed when it did not run.

Architecture changes should include an ADR under `docs/adr/`.
