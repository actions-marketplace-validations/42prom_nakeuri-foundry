from __future__ import annotations
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from .safe_paths import relative_inside

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def git_commit(root:Path)->str|None:
    try:
        p=subprocess.run(['git','rev-parse','HEAD'],cwd=root,text=True,capture_output=True,timeout=5)
        return p.stdout.strip() if p.returncode==0 else None
    except Exception:return None
def make_evidence(root:Path, kind:str, result:str, command:str|None=None, artifact:Path|None=None, metadata:dict[str,Any]|None=None)->dict[str,Any]:
    ev={"schema":"foundry/evidence/v1","kind":kind,"result":result.upper(),"timestamp":datetime.now(timezone.utc).isoformat(),"commit":git_commit(root),"command":command,"metadata":metadata or {}}
    if artifact and artifact.exists():
        ev['artifact']={"path":relative_inside(root, artifact),"sha256":sha256_file(artifact),"size":artifact.stat().st_size}
    return ev
def validate_evidence(ev:dict[str,Any], kind:str|None=None)->tuple[bool,str]:
    req={'schema','kind','result','timestamp','commit','metadata'}
    missing=req-set(ev)
    if missing:return False,f"missing fields: {sorted(missing)}"
    if ev.get('schema')!='foundry/evidence/v1':return False,'unsupported schema'
    if kind and ev.get('kind')!=kind:return False,'wrong evidence kind'
    if ev.get('result') not in {'PASS','FAIL','WARN'}:return False,'invalid result'
    if not ev.get('commit'):return False,'evidence is not bound to a git commit'
    return True,'ok'
def load_evidence_dir(root:Path)->list[dict[str,Any]]:
    base=root/'.factory'/'evidence'; out=[]
    if not base.exists(): return out
    for p in sorted(base.glob('*.json')):
        try: out.append(json.loads(p.read_text(encoding='utf-8')))
        except Exception: pass
    return out
