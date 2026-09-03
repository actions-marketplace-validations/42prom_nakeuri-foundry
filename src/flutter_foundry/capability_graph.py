from __future__ import annotations
import json,re
from pathlib import Path
from typing import Any
DEFAULT_GRAPH={"schema":"foundry/capability-graph/v1","capabilities":{},"facts":{},"journeys":{}}
def _path(root:Path)->Path:return root.resolve()/'.factory'/'graph'/'capabilities.json'
def load_graph(root:Path)->dict[str,Any]:
    p=_path(root); return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {"schema":"foundry/capability-graph/v1","capabilities":{},"facts":{},"journeys":{}}
def save_graph(root:Path,graph:dict[str,Any])->None:
    p=_path(root); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(graph,indent=2,sort_keys=True)+"\n",encoding='utf-8')
def register_capability(root:Path,capability_id:str,owner:str,provides:list[str],canonical_files:list[str]|None=None,invariants:list[str]|None=None)->dict[str,Any]:
    g=load_graph(root);caps=g.setdefault('capabilities',{})
    if capability_id in caps:raise ValueError(f'capability already exists: {capability_id}')
    wanted=set(provides);overlap=[]
    for cid,c in caps.items():
        shared=wanted&set(c.get('provides',[]))
        if shared:overlap.append({"capability":cid,"shared":sorted(shared)})
    if overlap:return {"status":"conflict","conflicts":overlap}
    caps[capability_id]={"owner":owner,"provides":provides,"canonical_files":canonical_files or [],"invariants":invariants or [],"consumers":[]};save_graph(root,g)
    return {"status":"pass","capability":capability_id}
def resolve_intent(root:Path,intent:str)->dict[str,Any]:
    g=load_graph(root);terms={x for x in re.findall(r'[a-z0-9_]+',intent.lower()) if len(x)>2};scored=[]
    for cid,c in g.get('capabilities',{}).items():
        hay=' '.join([cid,c.get('owner',''),*c.get('provides',[]),*c.get('canonical_files',[])]).lower();score=sum(1 for t in terms if t in hay)
        if score:scored.append((score,cid,c))
    scored.sort(key=lambda x:(-x[0],x[1]))
    if not scored:return {"decision":"CREATE","matches":[],"reason":"no canonical capability matched"}
    return {"decision":"EXTEND_OR_REUSE","matches":[{"id":cid,"score":s,"owner":c.get('owner'),"provides":c.get('provides',[])} for s,cid,c in scored[:5]],"canonical":scored[0][1]}
def duplicate_capabilities(root:Path)->dict[str,Any]:
    g=load_graph(root);seen={};findings=[]
    for cid,c in g.get('capabilities',{}).items():
        for p in c.get('provides',[]):
            if p in seen and seen[p]!=cid:findings.append({"provide":p,"owners":[seen[p],cid]})
            seen[p]=cid
    return {"status":"fail" if findings else "pass","findings":findings}
