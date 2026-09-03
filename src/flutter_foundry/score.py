from __future__ import annotations
from typing import Any
from .evidence import validate_evidence

WEIGHTS={"functional":25,"architecture":15,"tests":15,"security":10,"performance":10,"ux_accessibility":10,"reliability":5,"supply_chain":5,"operability":3,"cost":2}
EVIDENCE_KIND={"functional":"acceptance","performance":"performance","ux_accessibility":"accessibility","reliability":"runtime","supply_chain":"supply_chain","operability":"operability","cost":"cost"}

def _valid_kind(evidence:list[dict[str,Any]],kind:str)->bool:
    return any(validate_evidence(e,kind)[0] and e.get('result')=='PASS' for e in evidence)
def release_score(verification:dict[str,Any], reviewer_blockers:int=0, reviewer_high:int=0, evidence:list[dict[str,Any]]|None=None, **legacy)->dict[str,Any]:
    evidence=evidence or []
    if reviewer_blockers:return {"score":0,"status":"blocked","reason":"reviewer blocker present","weights":WEIGHTS}
    checks={c['name']:c['status'] for c in verification.get('checks',[])}; points={}
    functional=_valid_kind(evidence,'acceptance') and checks.get('flutter_analyze')=='pass' and checks.get('dart_format')=='pass'
    tests=checks.get('flutter_test')=='pass' and verification.get('test_quality',{}).get('status')!='fail'
    architecture=checks.get('foundry_architecture')=='pass' and verification.get('clean_code',{}).get('status')!='fail' and verification.get('duplicate_guard',{}).get('status')!='fail'
    security=checks.get('foundry_security')=='pass'
    vals={
      'functional':25 if functional else 0,
      'architecture':15 if architecture else 0,
      'tests':15 if tests else 0,
      'security':10 if security else 0,
      'performance':10 if _valid_kind(evidence,'performance') else 0,
      'ux_accessibility':10 if _valid_kind(evidence,'accessibility') else 0,
      'reliability':5 if _valid_kind(evidence,'runtime') else 0,
      'supply_chain':5 if _valid_kind(evidence,'supply_chain') else 0,
      'operability':3 if _valid_kind(evidence,'operability') else 0,
      'cost':2 if _valid_kind(evidence,'cost') else 0,
    }
    score=sum(vals.values())
    if reviewer_high: score=min(score,79)
    blocking=verification.get('blocking',[])
    if blocking: return {"score":0,"status":"blocked","reason":"deterministic verification failure","blocking":blocking,"evidence":vals,"weights":WEIGHTS}
    status='pass' if score==100 and not reviewer_high else 'incomplete'
    return {"score":score,"status":status,"evidence":vals,"weights":WEIGHTS,"rule":"100 requires evidence-backed PASS in every weighted domain; booleans and model claims receive zero credit."}
