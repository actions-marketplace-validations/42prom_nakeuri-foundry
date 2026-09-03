from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

from .antigravity_native import install_antigravity_team, native_team_status
from .empirical_benchmark import BenchmarkProfile, compare_profiles
from .requirements import compile_requirements
from .scheduler import Scheduler


def scheduler_restart_fencing_drill(*, tasks:int=400, workers:int=24, crashes:int=60)->dict[str,Any]:
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);seed=Scheduler(root)
        for i in range(tasks):seed.create_task('restart-chaos',risk='MEDIUM',task_id=f'T-{i:04d}');seed.ready(f'T-{i:04d}')
        crash_ids={f'T-{i:04d}' for i in range(min(crashes,tasks))};crashed=set();done=set();stale_tokens={};stale_rejected=0;errors=[];lock=threading.Lock()
        def worker(idx:int):
            nonlocal stale_rejected
            owner=f'w{idx}'
            while True:
                s=Scheduler(root)  # new object each loop simulates scheduler/process restarts
                try:claim=s.claim_next(owner,30)
                except Exception as exc:
                    with lock:errors.append(str(exc));continue
                if not claim:return
                tid=claim['id'];token=claim.get('lease_token')
                old=None
                with lock:old=stale_tokens.get(tid)
                if old is not None:
                    try:Scheduler(root).finish_attempt(tid,'stale-worker',True,lease_token=old)
                    except ValueError:
                        with lock:stale_rejected+=1;stale_tokens.pop(tid,None)
                    else:
                        with lock:errors.append(f'stale completion unexpectedly accepted for {tid}')
                if tid in crash_ids and tid not in crashed:
                    with lock:crashed.add(tid);stale_tokens[tid]=token
                    con=sqlite3.connect(s.path);con.execute("UPDATE tasks SET lease_until='2000-01-01T00:00:00+00:00' WHERE id=?",(tid,));con.commit();con.close()
                    Scheduler(root).recover_expired_leases()
                    continue
                try:Scheduler(root).finish_attempt(tid,owner,True,lease_token=token)
                except Exception as exc:
                    with lock:errors.append(str(exc));continue
                with lock:done.add(tid)
        threads=[threading.Thread(target=worker,args=(i,)) for i in range(workers)]
        for t in threads:t.start()
        for t in threads:t.join()
        final=Scheduler(root)
        return {'status':'pass' if len(done)==tasks and len(crashed)==min(crashes,tasks) and stale_rejected==len(crashed) and not stale_tokens and not errors and final.verify_event_chain()['status']=='pass' else 'fail','tasks':tasks,'workers':workers,'crashes':len(crashed),'completed':len(done),'stale_completions_rejected':stale_rejected,'unreclaimed_stale':len(stale_tokens),'errors':errors[:10],'event_chain':final.verify_event_chain(),'integrity':final.integrity_check()}


def specification_oracle_drill()->dict[str,Any]:
    briefs=[
      'Add secure login with offline retry and push notification after successful sign in.',
      'Implement subscription billing with restore purchases and prevent duplicate fulfillment.',
      'Add camera QR scan and location permission with accessible responsive UI.',
      'Integrate backend API, realtime socket updates, cache and safe error logging.',
    ]*25
    ids=set();failures=[]
    for i,b in enumerate(briefs):
        out=compile_requirements(b);spec=out.get('executable_specification',{})
        local=spec.get('oracle_ids',[])
        if not local or len(local)!=len(set(local)):failures.append(f'{i}: missing/duplicate oracle ids')
        if not spec.get('requirements'):failures.append(f'{i}: no explicit requirements')
        ids.update((i,x) for x in local)
    return {'status':'pass' if not failures else 'fail','briefs':len(briefs),'oracle_instances':len(ids),'failures':failures[:20]}


def native_team_permission_drill()->dict[str,Any]:
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);install_antigravity_team(root);st=native_team_status(root)
        agents=root/'.agents'/'agents';violations=[]
        for p in agents.glob('*.md'):
            text=p.read_text(encoding='utf-8')
            reviewer=any(x in p.name for x in ('reviewer','arbiter','sentinel','explorer','architect','planner','verifier'))
            if reviewer and ('replace_file_content' in text or 'write_to_file' in text):violations.append(p.name)
        return {'status':'pass' if st['status']=='pass' and not violations else 'fail','team':st,'read_only_violations':violations}


def benchmark_harness_drill()->dict[str,Any]:
    with tempfile.TemporaryDirectory() as d:
        root=Path(d)/'repo';root.mkdir();subprocess.run(['git','init','-q'],cwd=root,check=True);subprocess.run(['git','config','user.email','bench@example.invalid'],cwd=root,check=True);subprocess.run(['git','config','user.name','Bench'],cwd=root,check=True)
        (root/'value.txt').write_text('bad\n');subprocess.run(['git','add','.'],cwd=root,check=True);subprocess.run(['git','commit','-qm','base'],cwd=root,check=True)
        runner=Path(d)/'runner.py';runner.write_text('''import json,sys\nfrom pathlib import Path\nreq=json.loads(Path(sys.argv[1]).read_text());w=Path(req["workspace"]);(w/"value.txt").write_text("good\\n");Path(sys.argv[2]).write_text(json.dumps({"status":"completed","usage":{"tokens":10,"cost_usd":0.01}}))\n''')
        checker=Path(d)/'check.py';checker.write_text('''from pathlib import Path\nimport sys\nsys.exit(0 if Path("value.txt").read_text().strip()=="good" else 1)\n''')
        profile=BenchmarkProfile('fake',(sys.executable,str(runner),'{request}','{response}'))
        tasks=[{'id':'B-1','repo':str(root),'base_commit':'HEAD','prompt':'fix value','token_budget':100,'cost_budget_usd':1,'hidden_acceptance':[{'name':'hidden','command':[sys.executable,str(checker)]}]}]
        out=compare_profiles([profile],tasks)
        return {'status':'pass' if out['summary']['fake']['accepted']==1 and out['results'][0]['fairness']['hidden_acceptance_not_sent_to_runner'] else 'fail','benchmark':out}


def v5_stress_suite()->dict[str,Any]:
    parts={'scheduler_restart_fencing':scheduler_restart_fencing_drill(),'specification_oracles':specification_oracle_drill(),'native_team_permissions':native_team_permission_drill(),'benchmark_harness':benchmark_harness_drill()}
    return {'status':'pass' if all(x.get('status')=='pass' for x in parts.values()) else 'fail','schema':'nakeuri/v5-stress-suite/v1','parts':parts,'claim_boundary':'These are real local code-path stress drills. They do not substitute for Docker/Kubernetes/device/store/head-to-head empirical runs.'}
