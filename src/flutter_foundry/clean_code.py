from __future__ import annotations
import re
from pathlib import Path
from typing import Any
from .util import safe_rel
FUNC_RE=re.compile(r'(?m)^\s*(?:Future<[^>]+>|Future<void>|void|bool|int|double|String|[A-Z]\w*(?:<[^>]+>)?)\s+(_?\w+)\s*\([^;]*\)\s*(?:async\s*)?\{')
CLASS_RE=re.compile(r'(?m)^\s*(?:abstract\s+)?class\s+(\w+)')
def _brace_span(text:str,start:int)->tuple[int,int]:
    i=text.find('{',start);depth=0
    if i<0:return(start,start)
    for j in range(i,len(text)):
        if text[j]=='{':depth+=1
        elif text[j]=='}':
            depth-=1
            if depth==0:return(i,j+1)
    return(i,len(text))
def scan_clean_code(root:Path)->dict[str,Any]:
    findings=[];dart_roots=[p for p in [root/'lib',root/'mobile'/'lib'] if p.exists()]
    for base in dart_roots:
        for p in base.rglob('*.dart'):
            text=p.read_text(encoding='utf-8',errors='ignore');rel=safe_rel(p,root);lines=text.splitlines()
            if len(lines)>500:findings.append({"severity":"medium","rule":"large-file","path":rel,"value":len(lines),"limit":500})
            for m in CLASS_RE.finditer(text):
                name=m.group(1)
                if re.match(r'Base(?:Repository|Service|Controller|Notifier)',name):findings.append({"severity":"high","rule":"speculative-base-abstraction","path":rel,"symbol":name})
                if name.endswith(('Manager','Coordinator','Factory')) and text.count(name)<=2:findings.append({"severity":"medium","rule":"single-use-orchestration-abstraction","path":rel,"symbol":name})
            for m in FUNC_RE.finditer(text):
                a,b=_brace_span(text,m.start());body=text[a:b];n=body.count('\n')+1;complexity=1+len(re.findall(r'\b(if|for|while|case|catch)\b|&&|\|\|',body))
                if n>80:findings.append({"severity":"medium","rule":"long-function","path":rel,"symbol":m.group(1),"lines":n,"limit":80})
                if complexity>15:findings.append({"severity":"medium","rule":"high-complexity","path":rel,"symbol":m.group(1),"complexity":complexity,"limit":15})
            if '/presentation/' in '/'+rel.replace('\\','/') and re.search(r'\b(Dio\(|http\.|\.get\(|\.post\(|\.put\(|\.delete\()',text):findings.append({"severity":"high","rule":"network-in-presentation","path":rel})
    return {"status":"fail" if any(f['severity']=='high' for f in findings) else "warn" if findings else "pass","findings":findings,"summary":{"total":len(findings),"high":sum(f['severity']=='high' for f in findings),"medium":sum(f['severity']=='medium' for f in findings)}}
