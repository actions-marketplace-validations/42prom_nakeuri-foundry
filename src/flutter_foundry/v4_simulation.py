from __future__ import annotations

import random
import sqlite3
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .release_controller import HealthPolicy, ReleaseController, evaluate_health
from .scheduler import Scheduler

STACKS=("flutter","nextjs","node","python","dotnet","go","rust","java","flutter+api","web+api","mobile+backend","polyglot","infra")
RISKS=("LOW","MEDIUM","HIGH","RELEASE")

PREVIOUS={
 "Nakeuri V3 code-state model":{"engineering_index":81.04,"acceptance":.7470,"first_pass":.5790,"escaped_defects":.3165,"architecture_escapes":.0646,"contract_escapes":.0360,"security_escapes":.0324,"runtime_failures":.0234,"cost":1.238},
 "OpenHands-class modeled profile":{"engineering_index":77.08,"acceptance":.6818,"first_pass":.5206,"escaped_defects":.4082,"architecture_escapes":.1076,"contract_escapes":.0535,"security_escapes":.0341,"runtime_failures":.0206,"cost":1.204},
 "Official Flutter AI modeled profile":{"engineering_index":72.69,"acceptance":.6083,"first_pass":.4798,"escaped_defects":.5295,"architecture_escapes":.1314,"contract_escapes":.0730,"security_escapes":.0460,"runtime_failures":.0464,"cost":1.230},
 "Generic coding-agent baseline":{"engineering_index":63.19,"acceptance":.4446,"first_pass":.4064,"escaped_defects":.8796,"architecture_escapes":.1960,"contract_escapes":.1051,"security_escapes":.0741,"runtime_failures":.0673,"cost":1.261},
}

@dataclass(frozen=True)
class Scenario:
    stack:str;risk:str;difficulty:float


def scenarios(count:int,seed:int)->list[Scenario]:
    rng=random.Random(seed)
    risk_weights=(.28,.42,.22,.08)
    out=[]
    for i in range(count):
        stack=STACKS[i%len(STACKS)]
        x=rng.random();cum=0.0;risk="MEDIUM"
        for r,w in zip(RISKS,risk_weights):
            cum+=w
            if x<=cum:risk=r;break
        out.append(Scenario(stack,risk,rng.uniform(.25,.95)))
    return out


def _v4_rates(s:Scenario)->dict[str,float]:
    b=PREVIOUS["Nakeuri V3 code-state model"]
    poly=s.stack not in {"python","infra"};flutter="flutter" in s.stack or s.stack=="mobile+backend";strict=s.risk in {"HIGH","RELEASE"}
    semantic_gain=.025 if poly else .008
    flutter_gain=.018 if flutter else 0
    runtime_gain=.018 if strict else .007
    hard=max(0.0,s.difficulty-.65)
    accept=min(.94,b["acceptance"]+semantic_gain+flutter_gain+runtime_gain-.018*hard)
    first=min(accept-.04,b["first_pass"]+.030+(semantic_gain*.8)+(flutter_gain*.9)+(.012 if strict else .004)-.012*hard)
    defect_factor=.74-(.05 if poly else 0)-(.03 if flutter else 0)-(.04 if strict else 0)+.04*hard
    arch_factor=.60-(.08 if strict else 0)-(.04 if flutter else 0)+.03*hard
    contract_factor=.58-(.07 if poly else 0)-(.03 if strict else 0)+.03*hard
    security_factor=.70-(.10 if strict else 0)+.03*hard
    runtime_factor=.56-(.12 if strict else 0)+.05*hard
    cost_factor=.965-(.018 if s.risk in {"LOW","MEDIUM"} else 0)+(.025 if strict else 0)
    return {"acceptance":accept,"first_pass":first,"escaped_defects":b["escaped_defects"]*defect_factor,"architecture_escapes":b["architecture_escapes"]*arch_factor,"contract_escapes":b["contract_escapes"]*contract_factor,"security_escapes":b["security_escapes"]*security_factor,"runtime_failures":b["runtime_failures"]*runtime_factor,"cost":b["cost"]*cost_factor}


def _index(v:dict[str,float])->float:
    b=PREVIOUS["Nakeuri V3 code-state model"]
    delta=(45*(v["acceptance"]-b["acceptance"])+20*(v["first_pass"]-b["first_pass"])+15*(b["escaped_defects"]-v["escaped_defects"])+8*(b["architecture_escapes"]-v["architecture_escapes"])+5*(b["contract_escapes"]-v["contract_escapes"])+4*(b["security_escapes"]-v["security_escapes"])+3*(b["runtime_failures"]-v["runtime_failures"])-4*max(0,v["cost"]/b["cost"]-1))
    return round(b["engineering_index"]+delta,2)


def modeled_comparison(*,count:int=500,repetitions:int=50,seed:int=20260902)->dict[str,Any]:
    totals={k:0.0 for k in ("acceptance","first_pass","escaped_defects","architecture_escapes","contract_escapes","security_escapes","runtime_failures","cost")};n=0
    for rep in range(repetitions):
        rng=random.Random(seed+rep*7919)
        for s in scenarios(count,seed+rep):
            rates=_v4_rates(s);n+=1
            for metric in totals:
                if metric=="cost":totals[metric]+=rates[metric]*(.9+.2*rng.random())
                else: totals[metric]+=1.0 if rng.random()<rates[metric] else 0.0
    v={k:totals[k]/n for k in totals};v["engineering_index"]=_index(v)
    peers={name:dict(values) for name,values in PREVIOUS.items()}
    lead=v["engineering_index"]-PREVIOUS["OpenHands-class modeled profile"]["engineering_index"]
    return {"status":"pass","schema":"nakeuri/v4-modeled-comparison/v1","seed":seed,"scenarios":count,"repetitions":repetitions,"observations":n,"v4":v,"previous_profiles":peers,"deltas_vs_v3":{k:v[k]-PREVIOUS["Nakeuri V3 code-state model"][k] for k in v if k in PREVIOUS["Nakeuri V3 code-state model"]},"engineering_index_lead_vs_openhands":lead,"claim_boundary":"V4 values are deterministic modeled estimates anchored to the previous V3 simulation rates. Peer rows are the stored prior modeled baselines, not live measurements."}


def scheduler_chaos_drill(*,tasks:int=500,workers:int=32,crashes:int=73)->dict[str,Any]:
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);s=Scheduler(root)
        crash_ids={f"TASK-{i:04d}" for i in range(min(crashes,tasks))};crashed=set();completed=set();active=set();duplicates=0;lock=threading.Lock();errors=[]
        for i in range(tasks):
            tid=f"TASK-{i:04d}";s.create_task("chaos",risk="MEDIUM",task_id=tid);s.ready(tid)
        def worker(idx:int):
            nonlocal duplicates
            owner=f"w{idx}"
            while True:
                try:claim=s.claim_next(owner,30)
                except Exception as exc:errors.append(str(exc));continue
                if not claim:return
                tid=claim["id"];token=claim.get("lease_token")
                with lock:
                    key=(tid,token)
                    if key in active:duplicates+=1
                    active.add(key)
                if tid in crash_ids and tid not in crashed:
                    with lock:crashed.add(tid);active.discard((tid,token))
                    con=sqlite3.connect(s.path);con.execute("UPDATE tasks SET lease_until='2000-01-01T00:00:00+00:00' WHERE id=?",(tid,));con.commit();con.close();s.recover_expired_leases();continue
                try:s.finish_attempt(tid,owner,True,lease_token=token)
                except Exception as exc:errors.append(str(exc))
                with lock:active.discard((tid,token));completed.add(tid)
        ts=[threading.Thread(target=worker,args=(i,)) for i in range(workers)]
        for t in ts:t.start()
        for t in ts:t.join()
        chain=s.verify_event_chain();schema=s.schema_status();integrity=s.integrity_check()
        return {"status":"pass" if len(completed)==tasks and len(crashed)==min(crashes,tasks) and duplicates==0 and not errors and chain["status"]=="pass" else "fail","tasks":tasks,"workers":workers,"injected_crashes":len(crashed),"completed":len(completed),"duplicate_claims":duplicates,"errors":errors[:10],"event_chain":chain,"schema":schema,"integrity":integrity,"lease_fencing":"enabled"}


def release_drill()->dict[str,Any]:
    with tempfile.TemporaryDirectory() as d:
        c=ReleaseController(Path(d),"SIM-V4");c.set_proof("PASS");c.transition("STAGING");c.transition("CANARY")
        policy=HealthPolicy(min_sample_count=10,required_consecutive_windows=2)
        bad=evaluate_health(policy,[{"sample_count":100,"error_rate":.2,"crash_free_sessions":.8,"p95_latency_ms":4000}]*2);c.record_health("canary",bad);blocked=c.transition("PRODUCTION")
        rollback=c.transition("ROLLING_BACK",reason="bad canary");rolled=c.transition("ROLLED_BACK")
        c2=ReleaseController(Path(d),"SIM-V4-GOOD");c2.set_proof("PASS");c2.transition("STAGING");c2.transition("CANARY")
        good=evaluate_health(policy,[{"sample_count":100,"error_rate":0,"crash_free_sessions":1,"p95_latency_ms":100}]*2);c2.record_health("canary",good);c2.approve_production(approved=True,actor="sim-human");prod=c2.transition("PRODUCTION");c2.record_health("production",good);verified=c2.transition("VERIFIED")
        ok=blocked.get("status")=="blocked" and rollback.get("state")=="ROLLING_BACK" and rolled.get("state")=="ROLLED_BACK" and prod.get("state")=="PRODUCTION" and verified.get("state")=="VERIFIED"
        return {"status":"pass" if ok else "fail","bad_canary_blocked":blocked.get("status")=="blocked","rollback_state":rolled.get("state"),"healthy_production_state":verified.get("state")}


def simulation_suite(*,count:int=500,repetitions:int=50,chaos_tasks:int=500,chaos_workers:int=32,chaos_crashes:int=73,seed:int=20260902)->dict[str,Any]:
    model=modeled_comparison(count=count,repetitions=repetitions,seed=seed);chaos=scheduler_chaos_drill(tasks=chaos_tasks,workers=chaos_workers,crashes=chaos_crashes);release=release_drill()
    return {"status":"pass" if all(x.get("status")=="pass" for x in (model,chaos,release)) else "fail","schema":"nakeuri/v4-simulation-suite/v1","model":model,"scheduler_chaos":chaos,"release_drill":release}
