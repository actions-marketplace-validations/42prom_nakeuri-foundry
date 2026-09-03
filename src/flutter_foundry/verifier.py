from __future__ import annotations

import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from .models import CheckResult
from .security import scan_project
from .security_assurance import run_security_assurance
from .architecture import architecture_scan
from .clean_code import scan_clean_code
from .design_guard import scan_design
from .duplicate_guard import scan_semantic_duplicates
from .test_quality import scan_test_quality
from .genome import validate_genome
from .invariants import verify_invariant_coverage
from .supply_chain import scan_supply_chain
from .production import validate_production_ops
from .visual_regression import validate_visual_contract
from .native_e2e import patrol_status, run_patrol
from .ci_plan import build_ci_plan


def _run(cwd:Path,name:str,cmd:list[str],timeout:int)->CheckResult:
    start=time.monotonic();exe=shutil.which(cmd[0])
    if not exe:return CheckResult(name=name,status='unavailable',command=' '.join(cmd),summary=f'{cmd[0]} not found on PATH')
    try:
        p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout)
        combined=(p.stdout+'\n'+p.stderr).strip()
        return CheckResult(name=name,status='pass' if p.returncode==0 else 'fail',command=' '.join(cmd),returncode=p.returncode,duration_ms=int((time.monotonic()-start)*1000),summary='\n'.join(combined.splitlines()[-30:])[-6000:])
    except subprocess.TimeoutExpired:return CheckResult(name=name,status='fail',command=' '.join(cmd),summary=f'timeout after {timeout}s')
    except OSError as e:return CheckResult(name=name,status='unavailable',command=' '.join(cmd),summary=str(e))


def _flutter_root(root:Path)->Path:
    if (root/'pubspec.yaml').exists():return root
    if (root/'mobile'/'pubspec.yaml').exists():return root/'mobile'
    return root


def _module_check(checks:list[CheckResult],name:str,result:dict[str,Any])->None:
    status=result.get('status','fail')
    checks.append(CheckResult(name=f'foundry_{name}',status='pass' if status=='pass' else 'fail' if status=='fail' else 'warn',summary=str(result.get('summary',result.get('findings',[])))[:5000]))


def _is_setup_command(command: list[str]) -> bool:
    """Keep verification deterministic and offline; setup belongs to CI/bootstrap."""
    prefixes = (
        ("flutter", "pub", "get"), ("npm", "ci"), ("pnpm", "install"),
        ("yarn", "install"), ("bun", "install"), ("uv", "sync"),
        ("poetry", "install"), ("python", "-m", "pip", "install"),
        ("dotnet", "restore"),
    )
    return any(tuple(command[:len(prefix)]) == prefix for prefix in prefixes)


def _check_name(surface: dict[str,Any], command: list[str]) -> str:
    sid = str(surface["id"])
    if command[:2] == ["dart", "format"]: return "dart_format"
    if command[:2] == ["flutter", "analyze"]: return "flutter_analyze"
    if command[:2] == ["flutter", "test"]: return "flutter_test"
    if command[:3] == ["flutter", "build", "appbundle"]: return "android_release_build"
    root = str(surface.get("root", ".")).replace("/", "_").replace(".", "root")
    action = "_".join(command[:3]).replace("-", "_")
    return f"{sid}_{root}_{action}"


def verify_project(root:Path,profile:str='standard')->dict[str,Any]:
    root=root.resolve(); app=_flutter_root(root)
    if profile not in {'fast','standard','release'}:raise ValueError('profile must be fast, standard, or release')
    checks=[]
    native_plan=build_ci_plan(root,profile)
    timeouts={"dart":120,"flutter":1200 if profile=='release' else 600,"npm":900,"pnpm":900,"yarn":900,"bun":900,"python":900,"dotnet":1200,"go":900,"cargo":1200,"mvn":1200,"gradle":1200,"./gradlew":1200,"./mvnw":1200,"ruff":300,"pyright":600}
    for plan in native_plan.get('plans',[]):
        surface=plan['surface'];cwd=root if surface['root']=='.' else root/surface['root']
        for command in plan.get('commands',[]):
            if _is_setup_command(command):continue
            checks.append(_run(cwd,_check_name(surface,command),command,timeouts.get(command[0],600)))
    modules={
      'architecture':architecture_scan(root),'security':scan_project(root),'clean_code':scan_clean_code(root),
      'design':scan_design(root),'duplicate_guard':scan_semantic_duplicates(root),'test_quality':scan_test_quality(root),
      'genome':validate_genome(root),'invariants':verify_invariant_coverage(root),
      'supply_chain':scan_supply_chain(root,release=profile=='release'),
      'native_ci_plan':native_plan,
    }
    if (root/'.factory'/'visual-contract.json').exists():modules['visual_contract']=validate_visual_contract(root)
    for key in ['architecture','security','clean_code','duplicate_guard','test_quality','genome','invariants','supply_chain']:
        _module_check(checks,key,modules[key])
    _module_check(checks,'native_ci_plan',native_plan)
    if 'visual_contract' in modules:_module_check(checks,'visual_contract',modules['visual_contract'])
    if profile=='release':
        modules['security_assurance']=run_security_assurance(root,release=True);_module_check(checks,'security_assurance',modules['security_assurance'])
        modules['production']=validate_production_ops(root);_module_check(checks,'production',modules['production'])
        has_flutter=any(p.get('surface',{}).get('id')=='flutter' for p in native_plan.get('plans',[]))
        if has_flutter:
            patrol=patrol_status(root)
            if patrol.get('configured'):
                pres=run_patrol(root)
                checks.append(CheckResult(name='patrol_native_e2e',status=pres.get('status','fail'),command=' '.join(pres.get('command',[])) if isinstance(pres.get('command'),list) else 'patrol test',summary=str(pres.get('summary',pres.get('reason','')))[:6000]))
                modules['patrol']=pres
            else:
                checks.append(CheckResult(name='patrol_native_e2e',status='unavailable',summary='Patrol not configured; required only when native critical journeys are declared by project policy'))
            if platform.system()=='Darwin' and shutil.which('xcodebuild'):
                checks.append(_run(app,'ios_release_build',['flutter','build','ios','--release','--no-codesign'],1200))
            else:checks.append(CheckResult(name='ios_release_build',status='unavailable',summary='requires macOS + Xcode'))
    blocking=[c for c in checks if c.status=='fail'];unavailable=[c for c in checks if c.status=='unavailable'];warnings=[c for c in checks if c.status=='warn']
    gaps=[c.name for c in unavailable+warnings]
    return {"profile":profile,"project_root":str(root),"flutter_root":str(app),"status":"fail" if blocking else "pass_with_gaps" if gaps else "pass","checks":[c.to_dict() for c in checks],"blocking":[c.name for c in blocking],"unavailable":[c.name for c in unavailable],"warnings":[c.name for c in warnings],"environment_gaps":gaps,**modules}
