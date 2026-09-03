---
name: foundry-bugfix
description: Repair a Flutter defect surgically using failing-first reproduction, blast-radius analysis, regression lock, and re-verification.
---
# Bugfix workflow
1. Reproduce or prove the defect from current evidence.
2. Identify the changed symbol and call `blast_radius` when applicable.
3. Write or identify a test/check that fails before the fix.
4. Make the smallest change that closes the defect.
5. Re-run the failing check, then the required verification profile.
6. Record a durable learning if the bug reveals a reusable pattern or false positive.
