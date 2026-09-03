from __future__ import annotations

from pathlib import Path
from typing import Any
from .architecture import architecture_scan
from .clean_code import scan_clean_code
from .design_guard import scan_design
from .duplicate_guard import scan_semantic_duplicates
from .security import scan_project
from .test_quality import scan_test_quality
from .genome import validate_genome
from .invariants import verify_invariant_coverage
from .visual_regression import validate_visual_contract
from .supply_chain import scan_supply_chain


def project_gate(root: Path, include_design: bool = True) -> dict[str, Any]:
    checks = {
        "architecture": architecture_scan(root),
        "clean_code": scan_clean_code(root),
        "duplicates": scan_semantic_duplicates(root),
        "security": scan_project(root),
        "test_quality": scan_test_quality(root),
        "genome": validate_genome(root),
        "invariants": verify_invariant_coverage(root),
        "supply_chain": scan_supply_chain(root, release=False),
    }
    if include_design:
        checks["design"] = scan_design(root)
        if (root / ".factory" / "visual-contract.json").exists(): checks["visual_regression_contract"] = validate_visual_contract(root)
    blocking = [name for name, result in checks.items() if result.get("status") == "fail"]
    return {"status": "fail" if blocking else "pass", "blocking": blocking, "checks": checks}
