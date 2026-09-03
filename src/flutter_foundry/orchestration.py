"""Compatibility facade for the durable Orchestration Kernel.

All task truth lives in Scheduler's SQLite store. This module preserves the original
public API without maintaining a second state file.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from .scheduler import Scheduler
from .worktrees import create_isolated_worktree

STATES={"DEFINED","READY","IMPLEMENTING","VERIFYING","REVIEWING","REPAIRING","MERGEABLE","MERGED","BLOCKED","CANCELLED","FAILED"}


def load_state(root:Path)->dict[str,Any]:
    s=Scheduler(root)
    with s._db() as con:
        rows=con.execute("SELECT id FROM tasks ORDER BY created_at,id").fetchall()
    tasks={r[0]:s.get(r[0]) for r in rows}
    return {"schema":"nakeuri-flutter-foundry/orchestration/v2","tasks":tasks,"events":s.events()}


def create_task(root:Path,title:str,risk:str="MEDIUM",depends_on:list[str]|None=None)->dict[str,Any]:
    return Scheduler(root).create_task(title,risk,depends_on or [])


def transition(root:Path,task_id:str,new_state:str,evidence:dict[str,Any]|None=None)->dict[str,Any]:
    new_state=new_state.upper()
    if new_state not in STATES: raise ValueError("invalid state")
    if new_state=="MERGEABLE":
        if not evidence or evidence.get("proof_status")!="pass" or int(evidence.get("review_blockers",0)):
            raise ValueError("MERGEABLE requires valid proof and zero blocker reviews")
    return Scheduler(root).transition(task_id,new_state,actor="compat-api",payload={"evidence_gate":bool(evidence)} if new_state=="MERGEABLE" else {})


def plan_dag(root:Path,tasks:list[dict[str,Any]])->dict[str,Any]:
    ids={t["id"] for t in tasks}; findings=[]; byid={t["id"]:t for t in tasks}
    for t in tasks:
        for dep in t.get("depends_on",[]):
            if dep not in ids: findings.append(f"{t['id']} depends on missing {dep}")
    temp=set();perm=set()
    def visit(x:str):
        if x in temp: findings.append(f"cycle at {x}"); return
        if x in perm:return
        temp.add(x)
        for dep in byid.get(x,{}).get("depends_on",[]): visit(dep)
        temp.remove(x);perm.add(x)
    for x in sorted(ids):visit(x)
    return {"status":"fail" if findings else "pass","findings":findings,"tasks":tasks}


def create_worktree(root:Path,task_id:str,branch:str|None=None)->dict[str,Any]:
    out=create_isolated_worktree(root,task_id,branch)
    if out.get("status")=="pass": Scheduler(root).attach_worktree(task_id,out["worktree"],out["branch"])
    return out
