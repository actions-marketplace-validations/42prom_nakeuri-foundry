from __future__ import annotations
import json
from pathlib import Path
from typing import Any
def _path(root:Path)->Path:return root.resolve()/'.factory'/'graph'/'invariants.json'
def load_invariants(root:Path)->dict[str,Any]:
    p=_path(root);return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {"schema":"foundry/invariants/v1","invariants":{}}
def register_invariant(root:Path,invariant_id:str,statement:str,owner:str,tests:list[str]|None=None,severity:str='high')->dict[str,Any]:
    data=load_invariants(root);inv=data.setdefault('invariants',{})
    if invariant_id in inv:raise ValueError(f'invariant already exists: {invariant_id}')
    inv[invariant_id]={"statement":statement,"owner":owner,"tests":tests or [],"severity":severity};p=_path(root);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding='utf-8');return {"status":"pass","invariant":invariant_id}
def verify_invariant_coverage(root:Path)->dict[str,Any]:
    data=load_invariants(root);findings=[]
    for iid,v in data.get('invariants',{}).items():
        if v.get('severity') in {'high','critical'} and not v.get('tests'):findings.append({"severity":"high","invariant":iid,"rule":"high-risk-invariant-without-test"})
    return {"status":"fail" if findings else "pass","findings":findings,"count":len(data.get('invariants',{}))}
