from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .budget import budget_policy


def _rows(root: Path) -> list[dict[str, Any]]:
    path = root.resolve() / ".factory" / "benchmarks" / "model-performance.jsonl"
    if not path.exists():
        return []
    out=[]
    for line in path.read_text(encoding="utf-8",errors="ignore").splitlines():
        try:
            row=json.loads(line)
            if isinstance(row,dict): out.append(row)
        except Exception: pass
    return out


def _wilson_lower(successes: int, n: int, z: float = 1.96) -> float:
    if n <= 0: return 0.0
    p=successes/n; den=1+(z*z/n)
    centre=p+(z*z/(2*n)); margin=z*math.sqrt((p*(1-p)+(z*z/(4*n)))/n)
    return max(0.0,(centre-margin)/den)


def model_performance(root: Path, task_class: str) -> list[dict[str, Any]]:
    grouped:dict[str,dict[str,float]]={}
    for row in _rows(root):
        if str(row.get("task_class"))!=task_class: continue
        model=str(row.get("model","")).strip()
        if not model: continue
        g=grouped.setdefault(model,{"samples":0,"accepted":0,"cost":0.0,"seconds":0.0,"tokens":0.0,"security_failures":0,"architecture_failures":0})
        g["samples"]+=1;g["accepted"]+=1 if row.get("accepted") else 0;g["cost"]+=float(row.get("cost_usd",0) or 0);g["seconds"]+=float(row.get("seconds",0) or 0);g["tokens"]+=float(row.get("tokens",0) or 0)
        g["security_failures"]+=1 if row.get("security_failure") else 0;g["architecture_failures"]+=1 if row.get("architecture_failure") else 0
    result=[]
    for model,g in grouped.items():
        n=int(g["samples"]); accepted=int(g["accepted"])
        result.append({"model":model,"samples":n,"acceptance_rate":round(accepted/n,4),"acceptance_lower_95":round(_wilson_lower(accepted,n),4),"avg_cost_usd":round(g["cost"]/n,6),"avg_seconds":round(g["seconds"]/n,3),"avg_tokens":round(g["tokens"]/n,1),"security_failure_rate":round(g["security_failures"]/n,4),"architecture_failure_rate":round(g["architecture_failures"]/n,4)})
    return sorted(result,key=lambda x:(-x["acceptance_lower_95"],-x["acceptance_rate"],x["avg_cost_usd"],x["avg_seconds"],x["model"]))



def record_model_outcome(root: Path, *, task_class: str, model: str, accepted: bool, cost_usd: float = 0.0, seconds: float = 0.0, tokens: int = 0, security_failure: bool = False, architecture_failure: bool = False, proof_ref: str = "") -> dict[str, Any]:
    if not task_class.strip() or not model.strip(): raise ValueError("task_class and model are required")
    if cost_usd < 0 or seconds < 0 or tokens < 0: raise ValueError("usage values must be non-negative")
    path=root.resolve()/".factory"/"benchmarks"/"model-performance.jsonl";path.parent.mkdir(parents=True,exist_ok=True)
    row={"schema":"nakeuri/model-outcome/v2","at":datetime.now(timezone.utc).isoformat(),"task_class":task_class.strip(),"model":model.strip(),"accepted":bool(accepted),"cost_usd":float(cost_usd),"seconds":float(seconds),"tokens":int(tokens),"security_failure":bool(security_failure),"architecture_failure":bool(architecture_failure),"proof_ref":proof_ref.strip()}
    with path.open("a",encoding="utf-8") as f:f.write(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n")
    return {"status":"pass","path":str(path),"record":row,"rule":"Only verified task outcomes should be recorded; proof_ref should bind high-risk samples to evidence."}

def route_model(root: Path,*,task_class:str,risk:str,candidates:list[str]|None=None,minimum_samples:int=10)->dict[str,Any]:
    risk=risk.upper();perf=model_performance(root,task_class)
    if candidates:
        allowed=set(candidates);perf=[p for p in perf if p["model"] in allowed]
    qualified=[p for p in perf if p["samples"]>=minimum_samples]
    policy=budget_policy(risk)
    if not qualified:
        return {"status":"degraded","selection":None,"fallback":"policy-tier","risk":risk,"task_class":task_class,"budget":policy,"reason":"insufficient verified model-history samples","candidates":perf}
    best=max(p["acceptance_lower_95"] for p in qualified)
    tolerance=0.005 if risk in {"HIGH","RELEASE"} else 0.015
    quality_band=[p for p in qualified if p["acceptance_lower_95"]>=best-tolerance]
    if risk in {"HIGH","RELEASE"}:
        safe=[p for p in quality_band if p["security_failure_rate"]==0 and p["architecture_failure_rate"]<=0.02]
        if safe: quality_band=safe
    max_cost=policy.get("max_cost_usd");affordable=[p for p in quality_band if max_cost is None or p["avg_cost_usd"]<=float(max_cost)] or quality_band
    affordable.sort(key=lambda p:(p["avg_cost_usd"],p["avg_seconds"],p["avg_tokens"],-p["acceptance_lower_95"],p["model"]))
    selected=affordable[0]
    verifier=None
    if risk in {"HIGH","RELEASE"}:
        alternatives=[p for p in qualified if p["model"]!=selected["model"]]
        alternatives.sort(key=lambda p:(-p["acceptance_lower_95"],p["security_failure_rate"],p["avg_cost_usd"]))
        verifier=alternatives[0]["model"] if alternatives else None
    confidence=min(1.0,math.log10(max(10,selected["samples"]))/2.0)
    return {"status":"pass","selection":selected["model"],"verification_model":verifier,"requires_independent_model_review":risk in {"HIGH","RELEASE"},"task_class":task_class,"risk":risk,"evidence":selected,"confidence":round(confidence,3),"quality_band":quality_band,"budget":policy,"rule":"Use conservative 95% quality evidence first; then cost/latency inside a risk-specific near-quality band. HIGH/RELEASE recommends an independent second model."}
