from __future__ import annotations
from typing import Any

BASE = ["happy-path", "validation-failure"]
SIGNALS = {
    "network": ["timeout", "offline", "5xx", "malformed-response"],
    "auth": ["401-expired-session", "refresh-failure", "logout-during-request"],
    "payment": ["duplicate-event", "late-callback", "cancelled-purchase", "restore-failure"],
    "sync": ["restart-mid-sync", "duplicate-mutation", "conflict", "connectivity-flap"],
    "realtime": ["disconnect", "reconnect", "duplicate-message", "out-of-order-event"],
    "permission": ["denied", "permanently-denied", "revoked-after-grant"],
    "storage": ["corrupt-local-state", "write-failure", "migration-failure"],
}


def build_fault_matrix(task: str, risk: str = "MEDIUM", capabilities: list[str] | None = None) -> dict[str, Any]:
    text=(task+' '+' '.join(capabilities or [])).lower();scenarios=list(BASE);matched=[]
    aliases={"network":["api","http","network"],"auth":["auth","token","session","login"],"payment":["payment","purchase","billing","subscription"],"sync":["sync","offline","outbox"],"realtime":["socket","realtime","chat"],"permission":["camera","permission","nfc","location","notification"],"storage":["storage","database","hive","sqlite","cache"]}
    for key,words in aliases.items():
        if any(w in text for w in words):matched.append(key);scenarios.extend(SIGNALS[key])
    if risk.upper()=='LOW':scenarios=[s for s in scenarios if s in BASE or s in {'denied','timeout'}]
    required_evidence='unit' if risk.upper()=='LOW' else 'integration' if risk.upper()=='MEDIUM' else 'runtime+integration'
    return {"risk":risk.upper(),"matched_surfaces":matched,"scenarios":list(dict.fromkeys(scenarios)),"required_evidence":required_evidence,"rule":"Only test failure modes relevant to the task; do not create speculative error machinery."}
