from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def init_visual_contract(root: Path, screens: list[dict[str,str]] | None = None, force: bool=False) -> Path:
    p=root.resolve()/'.factory'/'visual-contract.json'
    if p.exists() and not force:return p
    p.parent.mkdir(parents=True,exist_ok=True)
    data={"schema":"foundry/visual-contract/v1","screens":screens or [],"required_states":["loading","empty","error"],"text_scales":[1.0,2.0],"unexpected_drift_blocks":True}
    p.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8');return p


def validate_visual_contract(root: Path) -> dict[str,Any]:
    root=root.resolve();p=root/'.factory'/'visual-contract.json'
    if not p.exists():return {"status":"warn","findings":["visual contract not configured"]}
    try:data=json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:return {"status":"fail","findings":[f"invalid visual contract: {e}"]}
    findings=[]
    for screen in data.get('screens',[]):
        test=screen.get('golden_test')
        if not test:findings.append(f"{screen.get('id','screen')} missing golden_test")
        elif not (root/test).exists():findings.append(f"golden test missing: {test}")
    return {"status":"fail" if findings else "pass","findings":findings,"screens":len(data.get('screens',[]))}
