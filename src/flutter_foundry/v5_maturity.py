from __future__ import annotations
from pathlib import Path
from typing import Any


def _contains(p: Path,name: str,*needles: str)->bool:
    try:text=(p/name).read_text(encoding='utf-8')
    except Exception:return False
    return all(n in text for n in needles)


def v5_flagship_score(package_dir: Path)->dict[str,Any]:
    p=package_dir.resolve()
    criteria={
      'specification':[
        ('executable spec v2',_contains(p,'specification.py','nakeuri/executable-specification/v2','requirements')),
        ('requirement stable IDs',_contains(p,'specification.py','REQ','sha256')),
        ('negative failure cases',_contains(p,'specification.py','NEGATIVE_CASES','negative_cases')),
        ('non-functional oracles',_contains(p,'specification.py','NFR_HINTS','non_functional_requirements')),
        ('independent high-risk oracle contract',_contains(p,'specification.py','high_risk_test_oracles_are_independent_from_implementation_worker')),
      ],
      'antigravity_native':[
        ('workspace static agents',_contains(p,'antigravity_native.py','.agents','agents')),
        ('explicit tool whitelists',_contains(p,'antigravity_native.py','READ_TOOLS','WRITE_TOOLS')),
        ('model tier separation',_contains(p,'antigravity_native.py','model:','pro')),
        ('sandbox command policy',_contains(p,'antigravity_native.py','commandExecutionPolicy: sandbox')),
        ('bootstrap installs native team',_contains(p,'bootstrap.py','install_antigravity_team','native_team')),
        ('Antigravity headless lifecycle provider',_contains(p,'runtime_provider.py','AntigravityHeadlessProvider','--output-format','--agent','--sandbox')),
      ],
      'native_e2e':[
        ('Patrol discovery',_contains(p,'native_e2e.py','patrol_status','patrol.yaml')),
        ('Patrol execution',_contains(p,'native_e2e.py','run_patrol','patrol','test')),
        ('runtime evidence artifact',_contains(p,'native_e2e.py','patrol-runtime-evidence/v1')),
        ('release verifier integration',_contains(p,'verifier.py','patrol_native_e2e','run_patrol')),
      ],
      'distributed_provider':[
        ('Kubernetes real Job provider',_contains(p,'runtime_provider.py','KubernetesJobProvider','batch/v1')),
        ('Kubernetes non-root sandbox',_contains(p,'runtime_provider.py','runAsNonRoot','allowPrivilegeEscalation')),
        ('deny-by-default network policy',_contains(p,'runtime_provider.py','NetworkPolicy','Ingress','Egress')),
        ('default runtime exposes Kubernetes',_contains(p,'runtime_provider.py','KubernetesJobProvider()')),
      ],
      'defect_to_defense':[
        ('defense proposals',_contains(p,'defense_memory.py','defense-proposal/v1','propose_defense')),
        ('classification into deterministic defense',_contains(p,'defense_memory.py','regression-test','security-invariant','contract')),
        ('independent verification before promotion',_contains(p,'defense_memory.py','verification_ref','independent verification reference required')),
        ('policy defenses require human approval',_contains(p,'defense_memory.py','policy-changing defenses require explicit human approval')),
      ],
      'empirical_benchmark':[
        ('fresh clone per run',_contains(p,'empirical_benchmark.py','git','clone','--no-hardlinks')),
        ('hidden acceptance withheld',_contains(p,'empirical_benchmark.py','Hidden acceptance commands are intentionally not included')),
        ('same base commit contract',_contains(p,'empirical_benchmark.py','resolved_commit','requested_base')),
        ('token/cost budgets',_contains(p,'empirical_benchmark.py','token_budget','cost_budget_usd')),
        ('multi-profile comparison',_contains(p,'empirical_benchmark.py','compare_profiles','acceptance_rate')),
        ('resolved commit and machine fairness',_contains(p,'empirical_benchmark.py','resolved_commit','platform.machine')),
        ('ablation delta report',_contains(p,'empirical_benchmark.py','ablation_report','acceptance_delta_pp')),
      ],
      'claim_discipline':[
        ('benchmark requires actual runner execution',_contains(p,'empirical_benchmark.py','Peer superiority may be claimed only from actual runner executions')),
        ('V5 score is implementation only',True),
        ('V4 model retained only as historical model',_contains(p,'v4_simulation.py','not live measurements')),
      ],
    }
    out={};passed=total=0
    for category,rows in criteria.items():
        ok=sum(1 for _,v in rows if v);n=len(rows);passed+=ok;total+=n
        out[category]={'score':round(10*ok/n,2),'passed':ok,'total':n,'criteria':[{'name':name,'pass':v} for name,v in rows]}
    return {'status':'pass' if passed==total else 'partial','schema':'nakeuri/v5-flagship-score/v1','score':round(10*passed/total,2),'passed':passed,'total':total,'categories':out,'claim_boundary':'This is repository implementation coverage for V5 flagship-proof capabilities. It is not a live peer benchmark or production certification.'}
