from __future__ import annotations
from pathlib import Path
from typing import Literal
from mcp.server import MCPServer
from . import __version__
from .util import workspace_path
from .requirements import compile_requirements as _spec
from .project_inspector import inspect_project as _inspect
from .context_engine import context_for_task as _context
from .component_registry import ComponentRegistry
from .component_solver import solve_components as _solve
from .risk_engine import classify_risk as _risk
from .blast_radius import blast_radius as _blast
from .architecture import architecture_scan as _arch
from .security import scan_project as _sec
from .security_assurance import run_security_assurance as _security_assurance
from .clean_code import scan_clean_code as _clean
from .design_guard import scan_design as _design
from .duplicate_guard import scan_semantic_duplicates as _dupes
from .genome import validate_genome as _genome
from .capability_graph import resolve_intent as _resolve
from .invariants import verify_invariant_coverage as _inv
from .test_quality import scan_test_quality as _tq
from .verifier import verify_project as _verify
from .score import release_score as _score
from .evidence import load_evidence_dir
from .orchestration import create_task as _create_task,transition as _transition,load_state as _state
from .scheduler import Scheduler
from .product_compiler import write_product_definition as _product
from .delivery import install_delivery_plane as _delivery
from .gate import project_gate as _gate
from .platform_adapters import adapter_report as _platforms
from .production import validate_production_ops as _production
from .flutter_stack import official_stack_status as _flutter_stack
from .team import role_plan as _roles
from .fault_matrix import build_fault_matrix as _faults
from .supply_chain import scan_supply_chain as _supply
from .evidence_ledger import EvidenceLedger
from .agent_runtime import runtime_status as _runtime_status
from .lifecycle import LifecycleRunner
from .store_delivery import validate_store_delivery as _store_delivery, store_delivery_preflight as _store_preflight
from .maturity import implementation_coverage as _implementation_coverage
from .environment import environment_status as _environment_status
from .budget import budget_status as _budget_status
from .semantic_engine import semantic_project_graph as _semantic_graph, symbol_impact as _symbol_impact
from .security_posture import security_posture as _security_posture
from .distributed_runtime import WorkerRegistry
from .release_controller import ReleaseController
from .v3_maturity import v3_implementation_score as _v3_score
from .ci_plan import build_ci_plan as _ci_plan
from .runtime_provider import UnifiedLifecycleExecutor

mcp=MCPServer('Nakeuri Flutter Foundry',version=__version__,instructions='CLI-first, Docker-capable, polyglot, durable evidence-first engineering control plane with a flagship Flutter adapter. Deterministic gates outrank model opinion; reuse canonical capabilities before creating new ones; writers never approve their own work.')
def _root(project:str|None)->Path:return workspace_path(project)
@mcp.tool()
def compile_requirements(brief:str)->dict:return _spec(brief)
@mcp.tool()
def inspect_project(project:str|None=None)->dict:return _inspect(_root(project))
@mcp.tool()
def context_for_task(task:str,project:str|None=None,limit:int=12)->dict:return _context(_root(project),task,limit)
@mcp.tool()
def resolve_components(components:list[str],platforms:list[str]|None=None,max_risk:str='RELEASE')->dict:return _solve(components,platforms or ['android','ios'],max_risk)
@mcp.tool()
def resolve_capability(intent:str,project:str|None=None)->dict:return _resolve(_root(project),intent)
@mcp.tool()
def classify_risk(task:str,changed_files:int=0,call_sites:int=0,component_risks:list[str]|None=None)->dict:return _risk(task,changed_files,call_sites,component_risks).to_dict()
@mcp.tool()
def role_plan(risk:str,task:str='')->dict:return _roles(risk,task)
@mcp.tool()
def fault_matrix(task:str,risk:str='MEDIUM',capabilities:list[str]|None=None)->dict:return _faults(task,risk,capabilities)
@mcp.tool()
def blast_radius(symbol:str,project:str|None=None)->dict:return _blast(_root(project),symbol)
@mcp.tool()
def architecture_scan(project:str|None=None)->dict:return _arch(_root(project))
@mcp.tool()
def clean_code_scan(project:str|None=None)->dict:return _clean(_root(project))
@mcp.tool()
def design_consistency_scan(project:str|None=None)->dict:return _design(_root(project))
@mcp.tool()
def duplicate_intent_scan(project:str|None=None)->dict:return _dupes(_root(project))
@mcp.tool()
def genome_validate(project:str|None=None)->dict:return _genome(_root(project))
@mcp.tool()
def invariant_coverage(project:str|None=None)->dict:return _inv(_root(project))
@mcp.tool()
def test_quality_scan(project:str|None=None)->dict:return _tq(_root(project))
@mcp.tool()
def deterministic_gate(project:str|None=None)->dict:return _gate(_root(project))
@mcp.tool()
def supply_chain_scan(release:bool=False,project:str|None=None)->dict:return _supply(_root(project),release)
@mcp.tool()
def external_security_assurance(release:bool=False,project:str|None=None)->dict:return _security_assurance(_root(project),release)
@mcp.tool()
def platform_status(project:str|None=None)->dict:return _platforms(_root(project))
@mcp.tool()
def official_flutter_stack_status(project:str|None=None)->dict:return _flutter_stack(_root(project))
@mcp.tool()
def production_readiness(project:str|None=None)->dict:return _production(_root(project))
@mcp.tool()
def verify_project(profile:Literal['fast','standard','release']='standard',project:str|None=None)->dict:return _verify(_root(project),profile)
@mcp.tool()
def release_score(profile:Literal['fast','standard','release']='release',project:str|None=None)->dict:return _score(_verify(_root(project),profile),evidence=load_evidence_dir(_root(project)))
@mcp.tool()
def orchestration_create_task(title:str,risk:str='MEDIUM',depends_on:list[str]|None=None,project:str|None=None)->dict:return _create_task(_root(project),title,risk,depends_on)
@mcp.tool()
def orchestration_transition(task_id:str,state:str,proof_status:str|None=None,review_blockers:int=0,project:str|None=None)->dict:return _transition(_root(project),task_id,state,{'proof_status':proof_status,'review_blockers':review_blockers})
@mcp.tool()
def orchestration_state(project:str|None=None)->dict:return _state(_root(project))
@mcp.tool()
def scheduler_claim(worker:str,lease_seconds:int=900,project:str|None=None)->dict|None:return Scheduler(_root(project)).claim_next(worker,lease_seconds)
@mcp.tool()
def scheduler_heartbeat(task_id:str,worker:str,lease_seconds:int=900,project:str|None=None)->dict:return Scheduler(_root(project)).heartbeat(task_id,worker,lease_seconds)
@mcp.tool()
def evidence_ledger_verify(project:str|None=None)->dict:return EvidenceLedger(_root(project)).verify()
@mcp.tool()
def define_product(brief:str,project:str|None=None)->dict:return _product(_root(project),brief)
@mcp.tool()
def install_delivery(project:str|None=None)->dict:return _delivery(_root(project))
@mcp.tool()
def agent_runtime_status()->dict:return _runtime_status()
@mcp.tool()
def environment_readiness(project:str|None=None,probe_docker:bool=False)->dict:return _environment_status(_root(project),probe_docker)
@mcp.tool()
def task_budget_status(task_id:str,risk:str,project:str|None=None)->dict:return _budget_status(_root(project),task_id,risk)
@mcp.tool()
def store_delivery_status(project:str|None=None)->dict:return _store_delivery(_root(project))
@mcp.tool()
def store_delivery_preflight(platform:Literal['android','ios'],project:str|None=None)->dict:return _store_preflight(_root(project),platform)
@mcp.tool()
def implementation_capability_coverage()->dict:return _implementation_coverage(Path(__file__).resolve().parent)
def _run_lifecycle(worker:str,model:str|None,project:str|None,provider:str|None)->dict:
    executor=UnifiedLifecycleExecutor.default(model=model,preferred=provider)
    return LifecycleRunner(_root(project),executor).run_next(worker)
@mcp.tool()
def lifecycle_run(worker:str='foundry-worker',model:str|None=None,provider:Literal['antigravity','docker','openhands','kubernetes']|None=None,project:str|None=None)->dict:
    return _run_lifecycle(worker,model,project,provider)
@mcp.tool()
def lifecycle_run_openhands(worker:str='openhands-worker',model:str|None=None,project:str|None=None)->dict:
    """Compatibility alias; execution still passes through unified provider policy."""
    return _run_lifecycle(worker,model,project,'openhands')
@mcp.tool()
def semantic_graph(project:str|None=None)->dict:return _semantic_graph(_root(project))
@mcp.tool()
def semantic_symbol_impact(symbol:str,project:str|None=None)->dict:return _symbol_impact(_root(project),symbol)
@mcp.tool()
def security_posture(release:bool=False,project:str|None=None)->dict:return _security_posture(_root(project),release=release)
@mcp.tool()
def distributed_worker_status(project:str|None=None)->dict:return WorkerRegistry(_root(project)).status()
@mcp.tool()
def distributed_worker_reserve(risk:str,platform:str|None=None,provider:str|None=None,task_id:str|None=None,slots:int=1,project:str|None=None)->dict:
    return WorkerRegistry(_root(project)).reserve(risk=risk,platform=platform,provider=provider,task_id=task_id,slots=slots)
@mcp.tool()
def orchestration_event_chain(project:str|None=None)->dict:return Scheduler(_root(project)).verify_event_chain()
@mcp.tool()
def release_control_status(release_id:str,project:str|None=None)->dict:return ReleaseController(_root(project),release_id).status()
@mcp.tool()
def native_ci_plan(profile:Literal['fast','standard','release']='standard',project:str|None=None)->dict:return _ci_plan(_root(project),profile)
@mcp.tool()
def v3_target_implementation_score()->dict:return _v3_score(Path(__file__).resolve().parent)

def main():mcp.run()
if __name__=='__main__':main()
