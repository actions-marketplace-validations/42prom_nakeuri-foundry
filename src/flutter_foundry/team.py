from __future__ import annotations
from typing import Any

ROLE_POLICY={
 "sentinel":{"write":False,"model":"pro","purpose":"specification/oracle"},
 "explorer":{"write":False,"model":"flash","purpose":"context/ownership"},
 "architect":{"write":False,"model":"pro","purpose":"architecture/invariants"},
 "test-planner":{"write":False,"model":"pro","purpose":"independent acceptance oracle"},
 "flutter-worker":{"write":True,"model":"inherit","purpose":"flutter implementation"},
 "backend-worker":{"write":True,"model":"inherit","purpose":"backend/data implementation"},
 "reviewer":{"write":False,"model":"pro","purpose":"independent correctness"},
 "security-reviewer":{"write":False,"model":"pro","purpose":"security/privacy"},
 "test-reviewer":{"write":False,"model":"pro","purpose":"test quality"},
 "simplicity-reviewer":{"write":False,"model":"flash","purpose":"minimality"},
 "runtime-verifier":{"write":False,"model":"inherit","purpose":"runtime/native evidence"},
 "release-verifier":{"write":False,"model":"pro","purpose":"release evidence"},
 "merge-arbiter":{"write":False,"model":"pro","purpose":"evidence-only decision"},
}


def role_plan(risk: str, task: str = "") -> dict[str, Any]:
    """Stable provider-neutral lifecycle roles retained for backward compatibility."""
    risk = risk.upper()
    if risk == "LOW":
        roles = ["worker"]; review = "deterministic-gates"; human = False
    elif risk == "MEDIUM":
        roles = ["explorer", "worker", "reviewer"]; review = "independent-model-review"; human = False
    elif risk == "HIGH":
        roles = ["explorer", "architect", "test-designer", "worker", "reviewer", "security-reviewer"]; review = "independent-multi-lens-review"; human = True
    elif risk == "RELEASE":
        roles = ["release-planner", "worker", "reviewer", "security-reviewer", "release-verifier"]; review = "independent-release-review"; human = True
    else: raise ValueError(f"unknown risk: {risk}")
    return {"risk":risk,"task":task,"roles":roles,"writer":"worker","review_policy":review,"human_merge_required":human,"rule":"writers never approve their own work"}


def native_role_plan(risk: str, task: str = "", *, surfaces: list[str] | None=None) -> dict[str, Any]:
    """Antigravity-native specialist team with explicit permission/model separation."""
    risk=risk.upper();surfaces=surfaces or ["flutter"]
    worker="flutter-worker" if "flutter" in surfaces else "backend-worker"
    if risk=="LOW": roles=[worker,"runtime-verifier"];review="deterministic-gates";human=False
    elif risk=="MEDIUM": roles=["sentinel","explorer","test-planner",worker,"reviewer","runtime-verifier","merge-arbiter"];review="independent-model-review";human=False
    elif risk=="HIGH": roles=["sentinel","explorer","architect","test-planner",worker,"reviewer","security-reviewer","test-reviewer","simplicity-reviewer","runtime-verifier","merge-arbiter"];review="independent-multi-lens-review";human=True
    elif risk=="RELEASE": roles=["sentinel","architect","test-planner",worker,"reviewer","security-reviewer","test-reviewer","runtime-verifier","release-verifier","merge-arbiter"];review="independent-release-review";human=True
    else: raise ValueError(f"unknown risk: {risk}")
    return {"risk":risk,"task":task,"roles":roles,"writer":worker,"review_policy":review,"human_merge_required":human,"role_policy":{r:ROLE_POLICY[r] for r in roles},"workspace_policy":{"writer":"branch","independent_reviewers":"read-only/inherit-or-separate-branch","high_risk_oracle_independent":risk in {"HIGH","RELEASE"}},"rule":"writers never approve their own work; HIGH/RELEASE acceptance oracle is independent of implementation"}
