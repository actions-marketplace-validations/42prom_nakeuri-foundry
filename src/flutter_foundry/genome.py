from __future__ import annotations
import json
from pathlib import Path
from typing import Any

GENOME_FILES = ["product","domain","design","ux","architecture","data","api","security","testing","delivery"]
DEFAULTS: dict[str, dict[str, Any]] = {
    "product": {"vision":"", "actors":[], "core_journeys":[], "anti_features":[], "success_metrics":[]},
    "domain": {"entities":[], "capabilities":[], "invariants":[], "terminology":{}},
    "design": {"tokens":{"spacing":{"xs":4,"sm":8,"md":16,"lg":24,"xl":32},"radius":{"sm":8,"md":12,"lg":20}}, "canonical_components":{}, "forbid_raw_styles":True},
    "ux": {"interaction_grammar":{"loading":"canonical","empty":"canonical","error":"canonical","destructive":"confirm"},"accessibility":{"semantics":True,"text_scale":2.0}},
    "architecture": {"feature_first":True,"single_state_system":"riverpod","network_client":"dio","max_nesting":5,"forbid_speculative_abstractions":True},
    "data": {"single_source_of_truth":True,"offline_policy":"explicit","migration_policy":"forward-compatible"},
    "api": {"canonical_endpoints":{},"idempotency_for_mutations":True,"typed_errors":True},
    "security": {"least_privilege":True,"secrets_in_repo":False,"high_risk_requires_security_review":True},
    "testing": {"risk_adaptive":True,"regression_for_bugfix":True,"independent_test_design_for_high_risk":True},
    "delivery": {"pr_only":True,"required_green_ci":True,"staged_release":True,"rollback_required":True}
}

def init_genome(root: Path, overwrite: bool=False) -> dict[str, Any]:
    base=root.resolve()/'.factory'/'genome'; base.mkdir(parents=True,exist_ok=True)
    created=[]
    for name in GENOME_FILES:
        p=base/f'{name}.json'
        if overwrite or not p.exists():
            p.write_text(json.dumps({"schema":f"foundry/genome/{name}/v1", **DEFAULTS[name]}, indent=2)+"\n",encoding='utf-8')
            created.append(str(p.relative_to(root)))
    return {"status":"pass","created":created,"genome_dir":str(base)}

def load_genome(root: Path) -> dict[str, Any]:
    base=root.resolve()/'.factory'/'genome'; out={}; missing=[]
    for name in GENOME_FILES:
        p=base/f'{name}.json'
        if not p.exists(): missing.append(name); continue
        out[name]=json.loads(p.read_text(encoding='utf-8'))
    return {"status":"pass" if not missing else "incomplete","missing":missing,"genome":out}

def validate_genome(root: Path) -> dict[str, Any]:
    data=load_genome(root); findings=[]
    for name in data['missing']: findings.append({"severity":"high","rule":"missing-genome-directive","directive":name})
    g=data['genome']; arch=g.get('architecture',{}); delivery=g.get('delivery',{}); security=g.get('security',{})
    if arch and not arch.get('feature_first',False): findings.append({"severity":"medium","rule":"feature-first-disabled"})
    if delivery and not delivery.get('pr_only',False): findings.append({"severity":"high","rule":"pr-only-disabled"})
    if security and security.get('secrets_in_repo',True): findings.append({"severity":"high","rule":"secrets-in-repo-allowed"})
    return {"status":"fail" if any(f['severity']=='high' for f in findings) else "warn" if findings else "pass","findings":findings,"loaded":sorted(g)}
