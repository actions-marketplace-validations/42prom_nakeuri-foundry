from __future__ import annotations
import fnmatch, json, subprocess
from pathlib import Path
from typing import Any

def changed_files(root:Path, base:str='HEAD~1')->list[str]:
    try:
        p=subprocess.run(['git','diff','--name-only',base,'HEAD'],cwd=root,text=True,capture_output=True,timeout=10)
        return [x for x in p.stdout.splitlines() if x.strip()] if p.returncode==0 else []
    except Exception: return []
def validate_change_intent(root:Path, intent_path:Path|None=None, files:list[str]|None=None)->dict[str,Any]:
    p=intent_path or (root/'.factory'/'change-intent.json')
    if not p.exists(): return {"status":"incomplete","findings":[{"severity":"high","rule":"missing-change-intent"}]}
    intent=json.loads(p.read_text(encoding='utf-8')); files=files if files is not None else changed_files(root,intent.get('base','HEAD~1'))
    allowed=intent.get('allowed_globs',[]); forbidden=intent.get('must_not_change_globs',[]); findings=[]
    for f in files:
        if any(fnmatch.fnmatch(f,pat) for pat in forbidden): findings.append({"severity":"high","path":f,"rule":"must-not-change"})
        elif allowed and not any(fnmatch.fnmatch(f,pat) for pat in allowed): findings.append({"severity":"medium","path":f,"rule":"outside-declared-scope"})
    return {"status":"fail" if any(x['severity']=='high' for x in findings) else "warn" if findings else "pass","files":files,"findings":findings,"task":intent.get('task')}
