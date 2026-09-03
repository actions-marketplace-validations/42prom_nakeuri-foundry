from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def _commit(root: Path) -> str | None:
    try:
        p=subprocess.run(['git','rev-parse','HEAD'],cwd=root,text=True,capture_output=True,timeout=5)
        return p.stdout.strip() if p.returncode==0 else None
    except Exception:return None


def write_snapshot(root: Path, symbols: list[dict[str, Any]], references: list[dict[str, Any]], source: str = "dart-mcp") -> dict[str, Any]:
    root=root.resolve(); commit=_commit(root)
    if not commit: return {"status":"fail","reason":"semantic snapshot must be bound to a git commit"}
    payload={"schema":"foundry/semantic-snapshot/v1","commit":commit,"source":source,"symbols":symbols,"references":references}
    p=root/'.factory'/'graph'/'semantic.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return {"status":"pass","path":str(p),"commit":commit,"symbols":len(symbols),"references":len(references)}


def load_snapshot(root: Path, require_current: bool = True) -> dict[str, Any]:
    root=root.resolve();p=root/'.factory'/'graph'/'semantic.json'
    if not p.exists():return {"status":"missing","symbols":[],"references":[]}
    try:data=json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:return {"status":"fail","reason":f"invalid snapshot: {e}","symbols":[],"references":[]}
    if data.get('schema')!='foundry/semantic-snapshot/v1':return {"status":"fail","reason":"unsupported schema",**data}
    current=_commit(root)
    if require_current and current and data.get('commit')!=current:return {"status":"stale","reason":"snapshot is not bound to current HEAD",**data}
    return {"status":"pass",**data}


def symbol_impact(root: Path, symbol: str) -> dict[str, Any] | None:
    snap=load_snapshot(root)
    if snap.get('status')!='pass':return None
    defs=[x for x in snap.get('symbols',[]) if x.get('name')==symbol]
    refs=[x for x in snap.get('references',[]) if x.get('symbol')==symbol]
    files=sorted({str(x.get('path')) for x in defs+refs if x.get('path')})
    level='safe' if len(files)<=3 else 'caution' if len(files)<=10 else 'risk'
    return {"symbol":symbol,"files":len(files),"occurrences":len(defs)+len(refs),"level":level,"definitions":defs,"references":refs,"matches":[{"path":p,"occurrences":sum(1 for x in defs+refs if x.get('path')==p)} for p in files],"source":"semantic-snapshot"}
