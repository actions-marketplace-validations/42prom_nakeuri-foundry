from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BenchmarkProfile:
    name: str
    command: tuple[str, ...]
    env: dict[str,str] | None = None


def _expand(parts: tuple[str,...], *, workspace: Path, request: Path, response: Path) -> list[str]:
    mapping={"{workspace}":str(workspace),"{request}":str(request),"{response}":str(response)}
    out=[]
    for part in parts:
        for key,val in mapping.items():part=part.replace(key,val)
        out.append(part)
    return out


def _run_check(cwd: Path, cmd: list[str], timeout: int) -> dict[str,Any]:
    start=time.monotonic()
    try:p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout)
    except subprocess.TimeoutExpired:return {"status":"fail","command":cmd,"reason":f"timeout after {timeout}s"}
    text=(p.stdout+"\n"+p.stderr).strip()
    return {"status":"pass" if p.returncode==0 else "fail","command":cmd,"returncode":p.returncode,"duration_ms":int((time.monotonic()-start)*1000),"summary":"\n".join(text.splitlines()[-40:])[-8000:]}


def _prepare_repo(repo: Path, base_commit: str, destination: Path) -> str:
    p=subprocess.run(["git","-c","safe.directory=*","clone","--no-hardlinks","--quiet",str(repo),str(destination)],text=True,capture_output=True)
    if p.returncode:
        if repo.is_dir() and (repo / ".git").exists():
            shutil.copytree(repo, destination, symlinks=True, ignore_dangling_symlinks=True)
        else:
            raise RuntimeError(p.stderr.strip() or "git clone failed")
    p=subprocess.run(["git","-c","safe.directory=*","checkout","--quiet",base_commit],cwd=destination,text=True,capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.strip() or "git checkout failed")
    p=subprocess.run(["git","-c","safe.directory=*","rev-parse","HEAD"],cwd=destination,text=True,capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.strip() or "git rev-parse failed")
    return p.stdout.strip()


def run_task(profile: BenchmarkProfile, task: dict[str,Any], *, timeout: int=1800) -> dict[str,Any]:
    repo=Path(task["repo"]).expanduser().resolve();base=str(task.get("base_commit","HEAD"))
    run_id=uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix="nakeuri-bench-") as d:
        work=Path(d)/"repo";resolved_commit=_prepare_repo(repo,base,work)
        request=Path(d)/"request.json";response=Path(d)/"response.json"
        # Hidden acceptance commands are intentionally not included in the runner request.
        request.write_text(json.dumps({
            "schema":"nakeuri/benchmark-runner-request/v1","task_id":task["id"],"prompt":task["prompt"],
            "workspace":str(work),"time_budget_seconds":int(task.get("time_budget_seconds",timeout)),
            "token_budget":task.get("token_budget"),"cost_budget_usd":task.get("cost_budget_usd"),
        },sort_keys=True)+"\n",encoding="utf-8")
        env=os.environ.copy();env.update(profile.env or {})
        cmd=_expand(profile.command,workspace=work,request=request,response=response)
        started=time.monotonic()
        try:proc=subprocess.run(cmd,cwd=work,text=True,capture_output=True,timeout=int(task.get("time_budget_seconds",timeout)),env=env)
        except subprocess.TimeoutExpired:
            return {"status":"fail","profile":profile.name,"task_id":task["id"],"reason":"runner timeout","accepted":False}
        runner_output=(proc.stdout+"\n"+proc.stderr).strip()
        runner={}
        if response.exists():
            try:runner=json.loads(response.read_text(encoding="utf-8"))
            except Exception:runner={"status":"invalid-response"}
        checks=[]
        for raw in task.get("hidden_acceptance",[]):
            command=[str(x) for x in raw["command"]]
            checks.append({"name":raw.get("name","acceptance"),**_run_check(work,command,int(raw.get("timeout",300)))})
        accepted=proc.returncode==0 and bool(checks) and all(x["status"]=="pass" for x in checks)
        usage=runner.get("usage",{}) if isinstance(runner,dict) and isinstance(runner.get("usage"),dict) else {}
        budget_violations=[]
        if task.get("token_budget") is not None:
            if usage.get("tokens") is None: budget_violations.append("tokens-unreported")
            elif float(usage["tokens"])>float(task["token_budget"]):budget_violations.append("tokens")
        if task.get("cost_budget_usd") is not None:
            if usage.get("cost_usd") is None: budget_violations.append("cost-unreported")
            elif float(usage["cost_usd"])>float(task["cost_budget_usd"]):budget_violations.append("cost")
        if budget_violations:accepted=False
        return {
            "status":"pass" if accepted else "fail","accepted":accepted,"profile":profile.name,"task_id":task["id"],"run_id":run_id,
            "runner_returncode":proc.returncode,"duration_ms":int((time.monotonic()-started)*1000),"usage":usage,"budget_violations":budget_violations,
            "acceptance":checks,"runner_summary":"\n".join(runner_output.splitlines()[-40:])[-8000:],"runner_response":runner,
            "fairness":{"requested_base":base,"resolved_commit":resolved_commit,"hidden_acceptance_not_sent_to_runner":True,"workspace_fresh_clone":True,"machine":{"system":platform.system(),"machine":platform.machine(),"python":platform.python_version()}},
        }


def compare_profiles(profiles: list[BenchmarkProfile], tasks: list[dict[str,Any]]) -> dict[str,Any]:
    rows=[]
    for task in tasks:
        for profile in profiles:rows.append(run_task(profile,task))
    summary={}
    for profile in profiles:
        mine=[r for r in rows if r["profile"]==profile.name]
        accepted=sum(1 for r in mine if r.get("accepted"))
        costs=[float(r.get("usage",{}).get("cost_usd",0) or 0) for r in mine]
        tokens=[float(r.get("usage",{}).get("tokens",0) or 0) for r in mine]
        summary[profile.name]={"tasks":len(mine),"accepted":accepted,"acceptance_rate":accepted/len(mine) if mine else 0,"total_cost_usd":sum(costs),"total_tokens":sum(tokens),"median_duration_ms":sorted([r["duration_ms"] for r in mine])[len(mine)//2] if mine else 0}
    return {"status":"pass","schema":"nakeuri/empirical-benchmark/v1","results":rows,"summary":summary,"claim_boundary":"Peer superiority may be claimed only from actual runner executions using the same task snapshots, hidden acceptance, budgets and machine class."}


def load_benchmark(path: Path) -> list[dict[str,Any]]:
    data=json.loads(path.read_text(encoding="utf-8"));tasks=data.get("tasks",data) if isinstance(data,dict) else data
    if not isinstance(tasks,list) or not tasks:raise ValueError("benchmark must contain a non-empty task list")
    required={"id","repo","prompt","hidden_acceptance"}
    for t in tasks:
        if not isinstance(t,dict) or not required.issubset(t):raise ValueError(f"invalid benchmark task: {t}")
        if not t["hidden_acceptance"]:raise ValueError(f"task {t['id']} must define hidden acceptance")
    return tasks


def ablation_report(comparison: dict[str,Any], baseline: str) -> dict[str,Any]:
    summary=comparison.get("summary",{})
    if baseline not in summary: raise ValueError(f"baseline profile not found: {baseline}")
    b=summary[baseline];rows={}
    for name,v in summary.items():
        rows[name]={
            "acceptance_delta_pp":round(100*(float(v.get("acceptance_rate",0))-float(b.get("acceptance_rate",0))),3),
            "cost_delta_usd":round(float(v.get("total_cost_usd",0))-float(b.get("total_cost_usd",0)),6),
            "token_delta":float(v.get("total_tokens",0))-float(b.get("total_tokens",0)),
            "duration_delta_ms":float(v.get("median_duration_ms",0))-float(b.get("median_duration_ms",0)),
        }
    return {"status":"pass","baseline":baseline,"profiles":rows,"rule":"An ablation is useful only when profiles differ by a documented component while task snapshots, hidden tests, budgets and machine class stay identical."}
