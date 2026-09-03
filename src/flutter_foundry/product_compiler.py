from __future__ import annotations
import json,re
from pathlib import Path
from typing import Any
from .requirements import compile_requirements
from .genome import init_genome

ROLE_HINTS={'admin':['admin','administrator','owner','manager'],'customer':['customer','user','member','client'],'staff':['staff','trainer','employee','operator']}

def compile_product(brief:str)->dict[str,Any]:
    req=compile_requirements(brief);text=brief.lower();actors=[]
    for role,hints in ROLE_HINTS.items():
        if any(h in text for h in hints):actors.append(role)
    if not actors:actors=['user']
    nouns=[x for x in re.findall(r'[a-zA-Z][a-zA-Z0-9_-]{3,}',brief) if x.lower() not in {'with','that','this','from','have','will','application','flutter'}]
    return {"schema":"foundry/product-hypothesis/v1","brief":brief,"actors":actors,"requirements":req,"domain_terms":list(dict.fromkeys(x.lower() for x in nouns[:20])),"status":"hypothesis","rule":"Product inference is not authority. Confirm material product decisions before implementation."}

def write_product_definition(root:Path,brief:str)->dict[str,Any]:
    root=root.resolve();init_genome(root);data=compile_product(brief);p=root/'.factory'/'product-definition.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2)+"\n",encoding='utf-8')
    gp=root/'.factory'/'genome'/'product.json';g=json.loads(gp.read_text());g['vision']=brief;g['actors']=data['actors'];gp.write_text(json.dumps(g,indent=2)+"\n")
    return {"status":"pass","path":str(p),"definition":data}
