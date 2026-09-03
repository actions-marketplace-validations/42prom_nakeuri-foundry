from __future__ import annotations
import json
from pathlib import Path
from typing import Any

def load_tasks(path:Path)->list[dict[str,Any]]:
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def summarize_results(path:Path)->dict[str,Any]:
    rows=load_tasks(path)
    if not rows:return {"count":0,"acceptance_rate":0.0,"first_pass_rate":0.0,"avg_cost":0.0,"avg_repair_iterations":0.0,"avg_tokens":0.0,"avg_seconds":0.0,"escaped_regressions":0,"architecture_violations":0,"duplicate_capabilities":0,"security_findings":0,"human_interventions":0}
    n=len(rows)
    passed=sum(bool(r.get('accepted')) for r in rows)
    first=sum(bool(r.get('accepted')) and int(r.get('repair_iterations',0))==0 for r in rows)
    def avg(name):return round(sum(float(r.get(name,0)) for r in rows)/n,4)
    def total(name):return sum(int(r.get(name,0)) for r in rows)
    return {
      "count":n,"acceptance_rate":round(passed/n,4),"first_pass_rate":round(first/n,4),
      "avg_cost":avg('cost'),"avg_repair_iterations":avg('repair_iterations'),"avg_tokens":avg('tokens'),"avg_seconds":avg('seconds'),
      "escaped_regressions":total('escaped_regressions'),"architecture_violations":total('architecture_violations'),
      "duplicate_capabilities":total('duplicate_capabilities'),"security_findings":total('security_findings'),"human_interventions":total('human_interventions'),
    }

def compare_runs(baseline:Path,candidate:Path)->dict[str,Any]:
    a=summarize_results(baseline);b=summarize_results(candidate)
    higher={"acceptance_rate","first_pass_rate"};metrics=["acceptance_rate","first_pass_rate","avg_cost","avg_repair_iterations","avg_tokens","avg_seconds","escaped_regressions","architecture_violations","duplicate_capabilities","security_findings","human_interventions"]
    delta={}
    for m in metrics:
        raw=round(float(b.get(m,0))-float(a.get(m,0)),4)
        delta[m]={"raw":raw,"better":raw>0 if m in higher else raw<0,"equal":raw==0}
    return {"baseline":a,"candidate":b,"delta":delta,"rule":"Use identical task corpus, model/provider policy, budgets and environment for a fair comparison."}
