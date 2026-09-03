from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _classify(description: str) -> tuple[str,str]:
    t=description.lower()
    if any(x in t for x in ("duplicate","replay","idempot","race","retry")):
        return "regression-test","Add a deterministic replay/concurrency regression that fails before the fix."
    if any(x in t for x in ("architecture","layer","dependency","ownership","duplicate source")):
        return "architecture-rule","Add or tighten a machine-checkable architecture/ownership rule."
    if any(x in t for x in ("auth","permission","secret","security","privacy","tenant")):
        return "security-invariant","Add a fail-closed invariant plus adversarial regression coverage."
    if any(x in t for x in ("schema","api","contract","migration","compat")):
        return "contract","Add a compatibility/contract oracle covering old and new consumers."
    return "regression-test","Add the smallest deterministic regression test that reproduces the escaped defect."


def propose_defense(root: Path, *, bug_id: str, description: str, evidence: str, affected: list[str]|None=None) -> dict[str, Any]:
    kind,action=_classify(description)
    proposal={"schema":"nakeuri/defense-proposal/v1","bug_id":bug_id,"description":description,"evidence":evidence,"affected":affected or [],"defense_kind":kind,"recommended_action":action,"status":"proposed","created_at":datetime.now(timezone.utc).isoformat(),"requires_independent_verification":True}
    p=root/".factory"/"defense-proposals"/f"{bug_id}.json";p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(proposal,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return {**proposal,"path":str(p)}


def promote_defense(root: Path, bug_id: str, *, verification_ref: str, human_approved: bool=False) -> dict[str, Any]:
    p=root/".factory"/"defense-proposals"/f"{bug_id}.json"
    if not p.exists():return {"status":"blocked","reason":"proposal not found"}
    data=json.loads(p.read_text(encoding="utf-8"))
    if not verification_ref.strip():return {"status":"blocked","reason":"independent verification reference required"}
    if data.get("defense_kind") in {"security-invariant","architecture-rule","contract"} and not human_approved:
        return {"status":"blocked","reason":"policy-changing defenses require explicit human approval"}
    data.update({"status":"promoted","verification_ref":verification_ref,"human_approved":human_approved,"promoted_at":datetime.now(timezone.utc).isoformat()})
    p.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    ledger=root/".factory"/"memory"/"defenses.jsonl";ledger.parent.mkdir(parents=True,exist_ok=True)
    with ledger.open("a",encoding="utf-8") as f:f.write(json.dumps(data,sort_keys=True)+"\n")
    return {"status":"pass","proposal":data,"ledger":str(ledger)}
