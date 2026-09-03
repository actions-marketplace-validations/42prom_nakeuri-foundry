from __future__ import annotations
from pathlib import Path
from typing import Any

def create_adr(root:Path,title:str,context:str,decision:str,consequences:str)->dict[str,Any]:
    base=root/'docs'/'adr';base.mkdir(parents=True,exist_ok=True);nums=[]
    for p in base.glob('[0-9][0-9][0-9][0-9]-*.md'):
        try:nums.append(int(p.name[:4]))
        except ValueError:pass
    n=max(nums,default=0)+1;slug='-'.join(x for x in ''.join(c.lower() if c.isalnum() else ' ' for c in title).split()[:8]);p=base/f'{n:04d}-{slug}.md'
    p.write_text(f'# ADR-{n:04d}: {title}\n\nStatus: Accepted\n\n## Context\n{context}\n\n## Decision\n{decision}\n\n## Consequences\n{consequences}\n',encoding='utf-8')
    return {"status":"pass","path":str(p)}
