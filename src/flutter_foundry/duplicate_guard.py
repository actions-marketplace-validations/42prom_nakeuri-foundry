from __future__ import annotations
import re
from pathlib import Path
from typing import Any
from .capability_graph import duplicate_capabilities
from .util import safe_rel

def _tokens(s:str)->set[str]: return {x for x in re.findall(r'[a-z0-9]+',s.lower()) if len(x)>2 and x not in {'class','final','const','void','future','return','string','widget'}}
def scan_semantic_duplicates(root:Path)->dict[str,Any]:
    findings=[]; symbols=[]
    for base in [p for p in [root/'lib',root/'mobile'/'lib'] if p.exists()]:
        for p in base.rglob('*.dart'):
            text=p.read_text(encoding='utf-8',errors='ignore'); rel=safe_rel(p,root)
            for kind,name in re.findall(r'\b(class|mixin|enum)\s+(\w+)',text): symbols.append((name,rel,_tokens(name)))
    for i,(a,pa,ta) in enumerate(symbols):
        for b,pb,tb in symbols[i+1:]:
            if pa==pb or not ta or not tb: continue
            sim=len(ta&tb)/max(1,len(ta|tb))
            if sim>=0.8 and a!=b: findings.append({"severity":"medium","rule":"similar-symbol-intent","symbols":[a,b],"paths":[pa,pb],"similarity":round(sim,2)})
    cap=duplicate_capabilities(root)
    for f in cap['findings']: findings.append({"severity":"high","rule":"duplicate-capability-owner",**f})
    return {"status":"fail" if any(f['severity']=='high' for f in findings) else "warn" if findings else "pass","findings":findings}
