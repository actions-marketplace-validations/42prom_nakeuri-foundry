from __future__ import annotations
import argparse,json,shutil,sys,importlib.util
from pathlib import Path
from .architecture import architecture_scan
from .blast_radius import blast_radius
from .bootstrap import bootstrap_project
from .capability_graph import register_capability,resolve_intent
from .change_intent import validate_change_intent
from .clean_code import scan_clean_code
from .component_registry import ComponentRegistry,ComponentError
from .context_engine import context_for_task
from .create_project import create_project
from .design_guard import scan_design
from .duplicate_guard import scan_semantic_duplicates
from .delivery import install_delivery_plane
from .product_compiler import write_product_definition
from .adr import create_adr
from .evidence import load_evidence_dir
from .genome import init_genome,validate_genome
from .invariants import register_invariant,verify_invariant_coverage
from .orchestration import create_task,transition,load_state
from .project_inspector import inspect_project
from .proof import build_proof,write_proof,validate_proof
from .requirements import compile_requirements
from .risk_engine import classify_risk
from .score import release_score
from .security import scan_project
from .security_assurance import run_security_assurance
from .test_quality import scan_test_quality
from .verifier import verify_project
from .scheduler import Scheduler
from .platform_adapters import adapter_report
from .component_solver import solve_components
from .production import init_production_ops, validate_production_ops
from .gate import project_gate
from .evidence_ledger import EvidenceLedger
from .flutter_stack import official_stack_status, lock_skills
from .team import role_plan, native_role_plan
from .fault_matrix import build_fault_matrix
from .maturity import implementation_coverage
from .supply_chain import scan_supply_chain
from .agent_runtime import OpenHandsAgentExecutor, runtime_status
from .lifecycle import LifecycleRunner
from .store_delivery import init_store_delivery, validate_store_delivery, store_delivery_preflight, execute_store_delivery
from .assurance import verify_assurance_archive
from .sbom import generate_cyclonedx_from_pub_deps
from .environment import environment_status
from .certification import certify_repository
from .budget import budget_status
from .maintenance import deep_doctor, backup_runtime, repair_runtime
from .compatibility import compatibility_status
from .upgrade import upgrade_project
from .reproducible_build import reproducible_build_check
from .hardening import adversarial_self_test
from .maturity_report import maturity_report
from .standards import init_standards_radar, standards_status, technology_radar
from .execution_fabric import fabric_status, choose_provider, authorize_side_effect
from .knowledge_graph import build_project_graph, write_project_graph, contract_status
from .production_graph import init_release_graph, release_plan
from .mcp_gateway import MCPServerPolicy, spec_compatibility
from .distributed_runtime import WorkerCapability, WorkerRegistry
from .migration_safety import assess_migration
from .v3_maturity import v3_implementation_score
from .ci_plan import build_ci_plan
from .polyglot_smoke import run_polyglot_smoke
from .semantic_engine import semantic_project_graph, symbol_impact
from .security_posture import security_posture
from .runtime_security import hardened_container_policy, validate_runtime_attestation
from .docker_runtime import DockerExecutor
from .release_controller import HealthPolicy, ReleaseController, evaluate_health
from .attestation import release_attestation_contract, validate_release_attestation
from .benchmark_v3 import write_target_corpus, validate_target_corpus
from .model_router import route_model, record_model_outcome
from .runtime_provider import UnifiedLifecycleExecutor, provider_runtime_status
from .flutter_intelligence import flutter_specialist_snapshot
from .v4_maturity import v4_hardening_score
from .v4_simulation import simulation_suite
from .target10 import target10_gate
from .source_fingerprint import repository_fingerprint
from .antigravity_native import install_antigravity_team, native_team_status
from .native_e2e import patrol_status, run_patrol
from .defense_memory import propose_defense, promote_defense
from .empirical_benchmark import BenchmarkProfile, compare_profiles, load_benchmark
from .v5_maturity import v5_flagship_score
from .v5_simulation import v5_stress_suite

_CI_MODE=False
_COMPACT=False
_ALLOW_GAPS=False

def _exit_code(v):
 status=str(v.get("status","pass")).lower() if isinstance(v,dict) else "pass"
 if status in {"pass","ready","completed","not_run"}: return 0
 if status in {"warn","partial","degraded","simulated","pass_with_gaps"}: return 10
 if status in {"blocked","unavailable","missing"}: return 20
 return 30

def emit(v):
 print(json.dumps(v,indent=None if _COMPACT else 2,sort_keys=True,separators=(",",":") if _COMPACT else None))
 if _CI_MODE:
  code=_exit_code(v)
  if _ALLOW_GAPS and code==10: code=0
  if code: raise SystemExit(code)

def doctor_status()->dict:
 tools={"git":shutil.which('git'),"dart":shutil.which('dart'),"flutter":shutil.which('flutter')}
 mcp_available=importlib.util.find_spec('mcp') is not None
 missing=[name for name,path in tools.items() if not path]
 if not mcp_available: missing.append('mcp-python-sdk')
 return {"python":sys.version.split()[0],**tools,"mcp_python_sdk":mcp_available,"missing":missing,"status":'ready' if not missing else 'partial'}
def parser():
 p=argparse.ArgumentParser(prog='nakeuri',description='Nakeuri Engineering Foundry — CLI-first, polyglot, evidence-first software engineering control plane');p.add_argument('--ci',action='store_true',help='machine mode with deterministic exit codes');p.add_argument('--allow-gaps',action='store_true',help='with --ci, allow warning/partial/pass_with_gaps results while still failing blocked/error results');p.add_argument('--compact',action='store_true',help='compact JSON output');sp=p.add_subparsers(dest='cmd',required=True);sp.add_parser('doctor')
 for name in ['inspect','security','architecture','clean','design','duplicates','tests-quality','genome-validate','invariants-verify','bootstrap','state','gate','platforms','production-check','production-init','ledger-verify','flutter-stack-status','skills-lock','supply-chain','store-delivery-check']:
  q=sp.add_parser(name);q.add_argument('project')
 q=sp.add_parser('genome-init');q.add_argument('project')
 q=sp.add_parser('create');q.add_argument('project');q.add_argument('--org',default='com.example');q.add_argument('--platforms',default='android,ios')
 q=sp.add_parser('spec');q.add_argument('--brief',required=True)
 q=sp.add_parser('context');q.add_argument('project');q.add_argument('--task',required=True);q.add_argument('--limit',type=int,default=12)
 q=sp.add_parser('risk');q.add_argument('project');q.add_argument('--task',required=True);q.add_argument('--files',type=int,default=0);q.add_argument('--call-sites',type=int,default=0)
 q=sp.add_parser('blast');q.add_argument('project');q.add_argument('--symbol',required=True)
 q=sp.add_parser('plan');q.add_argument('project');q.add_argument('--components',required=True)
 q=sp.add_parser('verify');q.add_argument('project');q.add_argument('--profile',choices=['fast','standard','release'],default='standard')
 q=sp.add_parser('security-assurance');q.add_argument('project');q.add_argument('--release',action='store_true')
 q=sp.add_parser('score');q.add_argument('project');q.add_argument('--profile',choices=['fast','standard','release'],default='release')
 q=sp.add_parser('capability-resolve');q.add_argument('project');q.add_argument('--intent',required=True)
 q=sp.add_parser('capability-add');q.add_argument('project');q.add_argument('--id',required=True);q.add_argument('--owner',required=True);q.add_argument('--provides',required=True)
 q=sp.add_parser('invariant-add');q.add_argument('project');q.add_argument('--id',required=True);q.add_argument('--owner',required=True);q.add_argument('--statement',required=True);q.add_argument('--tests',default='')
 q=sp.add_parser('intent-check');q.add_argument('project');q.add_argument('--file')
 q=sp.add_parser('task-create');q.add_argument('project');q.add_argument('--title',required=True);q.add_argument('--risk',default='MEDIUM');q.add_argument('--depends-on',default='')
 q=sp.add_parser('schedule-create');q.add_argument('project');q.add_argument('--title',required=True);q.add_argument('--risk',default='MEDIUM');q.add_argument('--depends-on',default='');q.add_argument('--max-attempts',type=int,default=2)
 q=sp.add_parser('schedule-ready');q.add_argument('project');q.add_argument('task_id')
 q=sp.add_parser('schedule-claim');q.add_argument('project');q.add_argument('--worker',required=True);q.add_argument('--lease-seconds',type=int,default=900)
 q=sp.add_parser('components-solve');q.add_argument('--components',required=True);q.add_argument('--platforms',default='android,ios');q.add_argument('--max-risk',default='RELEASE')
 q=sp.add_parser('task-transition');q.add_argument('project');q.add_argument('task_id');q.add_argument('state');q.add_argument('--proof-status');q.add_argument('--review-blockers',type=int,default=0)
 q=sp.add_parser('proof');q.add_argument('project');q.add_argument('--task-id',required=True);q.add_argument('--task',required=True);q.add_argument('--profile',default='standard')
 q=sp.add_parser('delivery-init');q.add_argument('project');q.add_argument('--force',action='store_true')
 q=sp.add_parser('product-init');q.add_argument('project');q.add_argument('--brief',required=True)
 q=sp.add_parser('adr');q.add_argument('project');q.add_argument('--title',required=True);q.add_argument('--context',required=True);q.add_argument('--decision',required=True);q.add_argument('--consequences',required=True)
 q=sp.add_parser('team-plan');q.add_argument('--risk',required=True);q.add_argument('--task',default='')
 q=sp.add_parser('fault-matrix');q.add_argument('--task',required=True);q.add_argument('--risk',default='MEDIUM');q.add_argument('--capabilities',default='')
 q=sp.add_parser('maturity-implementation')
 q=sp.add_parser('runtime-status')
 q=sp.add_parser('doctor-deep');q.add_argument('project',nargs='?',default='.');q.add_argument('--probe-docker',action='store_true')
 q=sp.add_parser('compatibility');q.add_argument('project',nargs='?',default='.')
 q=sp.add_parser('backup');q.add_argument('project')
 q=sp.add_parser('repair');q.add_argument('project')
 q=sp.add_parser('upgrade');q.add_argument('project');q.add_argument('--apply',action='store_true')
 q=sp.add_parser('reproducible-build');q.add_argument('project',nargs='?',default='.');q.add_argument('--skip-install-smoke',action='store_true')
 q=sp.add_parser('adversarial-self-test')
 q=sp.add_parser('maturity-report');q.add_argument('project',nargs='?',default='.');q.add_argument('--reproducible-build',action='store_true');q.add_argument('--probe-docker',action='store_true')
 q=sp.add_parser('environment');q.add_argument('project',nargs='?',default='.');q.add_argument('--probe-docker',action='store_true')
 q=sp.add_parser('certify');q.add_argument('project',nargs='?',default='.');q.add_argument('--skip-tests',action='store_true');q.add_argument('--probe-docker',action='store_true');q.add_argument('--reproducible-build',action='store_true')
 q=sp.add_parser('budget-status');q.add_argument('project');q.add_argument('task_id');q.add_argument('--risk',required=True)
 q=sp.add_parser('store-delivery-init');q.add_argument('project');q.add_argument('--force',action='store_true')
 q=sp.add_parser('store-delivery-preflight');q.add_argument('project');q.add_argument('--platform',choices=['android','ios'],required=True)
 q=sp.add_parser('store-delivery-execute');q.add_argument('project');q.add_argument('--platform',choices=['android','ios'],required=True);q.add_argument('--approved',action='store_true')
 q=sp.add_parser('lifecycle-run');q.add_argument('project');q.add_argument('--worker',default='foundry-worker');q.add_argument('--model');q.add_argument('--api-key');q.add_argument('--base-url');q.add_argument('--provider',choices=['docker','openhands','remote','kubernetes','github-runner'])
 q=sp.add_parser('lifecycle-approve');q.add_argument('project');q.add_argument('task_id');q.add_argument('--approved',action='store_true')
 q=sp.add_parser('assurance-verify');q.add_argument('archive')
 q=sp.add_parser('sbom-from-pub');q.add_argument('input');q.add_argument('--output',required=True)
 q=sp.add_parser('standards-init');q.add_argument('project');q.add_argument('--force',action='store_true')
 q=sp.add_parser('standards-status');q.add_argument('project')
 q=sp.add_parser('technology-radar');q.add_argument('project')
 q=sp.add_parser('fabric-status');q.add_argument('project',nargs='?',default='.')
 q=sp.add_parser('fabric-route');q.add_argument('--risk',required=True);q.add_argument('--provider');q.add_argument('--docker-healthy',action='store_true')
 q=sp.add_parser('side-effect-check');q.add_argument('--action',required=True);q.add_argument('--risk',required=True);q.add_argument('--approved',action='store_true');q.add_argument('--proof-status')
 q=sp.add_parser('knowledge-graph');q.add_argument('project');q.add_argument('--write',action='store_true')
 q=sp.add_parser('contracts-check');q.add_argument('project')
 q=sp.add_parser('release-graph-init');q.add_argument('project');q.add_argument('--force',action='store_true')
 q=sp.add_parser('release-plan');q.add_argument('project')
 q=sp.add_parser('mcp-spec');q.add_argument('--client-spec',default='2026-07-28');q.add_argument('--capabilities',default='')
 q=sp.add_parser('worker-register');q.add_argument('project');q.add_argument('--id',required=True);q.add_argument('--host',required=True);q.add_argument('--providers',default='worktree');q.add_argument('--platforms',default='');q.add_argument('--max-risk',default='MEDIUM');q.add_argument('--slots',type=int,default=1)
 q=sp.add_parser('worker-select');q.add_argument('project');q.add_argument('--risk',required=True);q.add_argument('--platform');q.add_argument('--provider')
 q=sp.add_parser('migration-assess');q.add_argument('file')
 q=sp.add_parser('v3-score')
 q=sp.add_parser('target-10');q.add_argument('project',nargs='?',default='.');q.add_argument('--reproducible-build',action='store_true');q.add_argument('--probe-docker',action='store_true');q.add_argument('--require-certification',action='store_true')
 q=sp.add_parser('source-fingerprint');q.add_argument('project',nargs='?',default='.')
 q=sp.add_parser('ci-plan');q.add_argument('project');q.add_argument('--profile',choices=['fast','standard','release'],default='standard')
 q=sp.add_parser('polyglot-smoke')
 q=sp.add_parser('semantic-graph');q.add_argument('project');q.add_argument('--fallback-only',action='store_true')
 q=sp.add_parser('symbol-impact');q.add_argument('project');q.add_argument('--symbol',required=True)
 q=sp.add_parser('security-posture');q.add_argument('project');q.add_argument('--release',action='store_true')
 q=sp.add_parser('worker-reserve');q.add_argument('project');q.add_argument('--risk',required=True);q.add_argument('--platform');q.add_argument('--provider');q.add_argument('--task-id');q.add_argument('--owner');q.add_argument('--slots',type=int,default=1);q.add_argument('--ttl-seconds',type=int,default=900)
 q=sp.add_parser('worker-release');q.add_argument('project');q.add_argument('reservation_id');q.add_argument('--owner')
 q=sp.add_parser('worker-status');q.add_argument('project')
 q=sp.add_parser('event-chain-verify');q.add_argument('project')
 q=sp.add_parser('task-replay');q.add_argument('project');q.add_argument('task_id')
 q=sp.add_parser('runtime-policy');q.add_argument('--risk',required=True);q.add_argument('--image',required=True);q.add_argument('--network-required',action='store_true');q.add_argument('--workspace-read-only',action='store_true')
 q=sp.add_parser('runtime-attestation-validate');q.add_argument('file');q.add_argument('--risk',required=True)
 q=sp.add_parser('release-control-status');q.add_argument('project');q.add_argument('release_id')
 q=sp.add_parser('release-control-proof');q.add_argument('project');q.add_argument('release_id');q.add_argument('--status',required=True)
 q=sp.add_parser('release-control-approve');q.add_argument('project');q.add_argument('release_id');q.add_argument('--actor',required=True);q.add_argument('--approved',action='store_true')
 q=sp.add_parser('release-control-health');q.add_argument('project');q.add_argument('release_id');q.add_argument('--stage',required=True);q.add_argument('--file',required=True)
 q=sp.add_parser('release-control-transition');q.add_argument('project');q.add_argument('release_id');q.add_argument('state');q.add_argument('--reason',default='')
 q=sp.add_parser('attestation-contract')
 q=sp.add_parser('attestation-validate');q.add_argument('file')
 q=sp.add_parser('benchmark-v3-write');q.add_argument('path');q.add_argument('--count',type=int,default=500)
 q=sp.add_parser('benchmark-v3-validate');q.add_argument('path');q.add_argument('--minimum',type=int,default=500)
 q=sp.add_parser('model-route');q.add_argument('project');q.add_argument('--task-class',required=True);q.add_argument('--risk',required=True);q.add_argument('--candidates',default='');q.add_argument('--minimum-samples',type=int,default=10)
 q=sp.add_parser('model-record');q.add_argument('project');q.add_argument('--task-class',required=True);q.add_argument('--model',required=True);q.add_argument('--accepted',action='store_true');q.add_argument('--cost-usd',type=float,default=0.0);q.add_argument('--seconds',type=float,default=0.0);q.add_argument('--tokens',type=int,default=0);q.add_argument('--security-failure',action='store_true');q.add_argument('--architecture-failure',action='store_true');q.add_argument('--proof-ref',default='')
 q=sp.add_parser('provider-runtime-status')
 q=sp.add_parser('flutter-intelligence');q.add_argument('project')
 q=sp.add_parser('v4-score')
 q=sp.add_parser('simulation-suite');q.add_argument('--count',type=int,default=500);q.add_argument('--repetitions',type=int,default=50);q.add_argument('--chaos-tasks',type=int,default=500);q.add_argument('--chaos-workers',type=int,default=32);q.add_argument('--chaos-crashes',type=int,default=73);q.add_argument('--seed',type=int,default=20260902)
 q=sp.add_parser('native-team-plan');q.add_argument('--risk',required=True);q.add_argument('--task',default='');q.add_argument('--surfaces',default='flutter')
 q=sp.add_parser('native-team-install');q.add_argument('project');q.add_argument('--no-overwrite',action='store_true')
 q=sp.add_parser('native-team-status');q.add_argument('project')
 q=sp.add_parser('patrol-status');q.add_argument('project')
 q=sp.add_parser('patrol-run');q.add_argument('project');q.add_argument('--target');q.add_argument('--device');q.add_argument('--timeout',type=int,default=1800)
 q=sp.add_parser('defense-propose');q.add_argument('project');q.add_argument('--bug-id',required=True);q.add_argument('--description',required=True);q.add_argument('--evidence',required=True);q.add_argument('--affected',default='')
 q=sp.add_parser('defense-promote');q.add_argument('project');q.add_argument('--bug-id',required=True);q.add_argument('--verification-ref',required=True);q.add_argument('--approved',action='store_true')
 q=sp.add_parser('empirical-benchmark');q.add_argument('benchmark');q.add_argument('--profiles',required=True,help='JSON file with [{name,command,env?}]')
 q=sp.add_parser('v5-score')
 q=sp.add_parser('v5-stress-suite')
 return p

def main():
 global _CI_MODE,_COMPACT,_ALLOW_GAPS
 a=parser().parse_args();_CI_MODE=bool(a.ci);_COMPACT=bool(a.compact);_ALLOW_GAPS=bool(a.allow_gaps)
 if a.cmd=='doctor':emit(doctor_status());return
 if a.cmd=='spec':emit(compile_requirements(a.brief));return
 if a.cmd=='team-plan':emit(role_plan(a.risk,a.task));return
 if a.cmd=='fault-matrix':emit(build_fault_matrix(a.task,a.risk,[x.strip() for x in a.capabilities.split(',') if x.strip()]));return
 if a.cmd=='maturity-implementation':emit(implementation_coverage(Path(__file__).resolve().parent));return
 if a.cmd=='runtime-status':emit(runtime_status());return
 if a.cmd=='provider-runtime-status':emit(provider_runtime_status());return
 if a.cmd=='doctor-deep':emit(deep_doctor(Path(a.project),a.probe_docker));return
 if a.cmd=='compatibility':emit(compatibility_status(Path(a.project)));return
 if a.cmd=='backup':emit(backup_runtime(Path(a.project)));return
 if a.cmd=='repair':emit(repair_runtime(Path(a.project)));return
 if a.cmd=='upgrade':emit(upgrade_project(Path(a.project),apply=a.apply));return
 if a.cmd=='reproducible-build':emit(reproducible_build_check(Path(a.project),not a.skip_install_smoke));return
 if a.cmd=='adversarial-self-test':emit(adversarial_self_test());return
 if a.cmd=='maturity-report':emit(maturity_report(Path(a.project),run_reproducible_build=a.reproducible_build,probe_docker=a.probe_docker));return
 if a.cmd=='environment':emit(environment_status(Path(a.project),a.probe_docker));return
 if a.cmd=='certify':emit(certify_repository(Path(a.project),not a.skip_tests,a.probe_docker,a.reproducible_build));return
 if a.cmd=='budget-status':emit(budget_status(Path(a.project),a.task_id,a.risk));return
 if a.cmd=='assurance-verify':emit(verify_assurance_archive(Path(a.archive)));return
 if a.cmd=='sbom-from-pub':emit(generate_cyclonedx_from_pub_deps(Path(a.input),Path(a.output)));return
 if a.cmd=='fabric-route':emit(choose_provider(a.risk,preferred=a.provider,docker_healthy=True if a.docker_healthy else None));return
 if a.cmd=='side-effect-check':emit(authorize_side_effect(a.action,risk=a.risk,human_approved=a.approved,proof_status=a.proof_status));return
 if a.cmd=='mcp-spec':emit(spec_compatibility(a.client_spec,[x.strip() for x in a.capabilities.split(',') if x.strip()]));return
 if a.cmd=='migration-assess':
  data=json.loads(Path(a.file).read_text(encoding='utf-8'));emit(assess_migration(data.get('migration',data),data.get('consumers',[])));return
 if a.cmd=='v3-score':emit(v3_implementation_score(Path(__file__).resolve().parent));return
 if a.cmd=='v4-score':emit(v4_hardening_score(Path(__file__).resolve().parent));return
 if a.cmd=='simulation-suite':emit(simulation_suite(count=a.count,repetitions=a.repetitions,chaos_tasks=a.chaos_tasks,chaos_workers=a.chaos_workers,chaos_crashes=a.chaos_crashes,seed=a.seed));return
 if a.cmd=='native-team-plan':emit(native_role_plan(a.risk,a.task,surfaces=[x.strip() for x in a.surfaces.split(',') if x.strip()]));return
 if a.cmd=='native-team-install':emit(install_antigravity_team(Path(a.project),overwrite=not a.no_overwrite));return
 if a.cmd=='native-team-status':emit(native_team_status(Path(a.project)));return
 if a.cmd=='patrol-status':emit(patrol_status(Path(a.project)));return
 if a.cmd=='patrol-run':emit(run_patrol(Path(a.project),target=a.target,device=a.device,timeout=a.timeout));return
 if a.cmd=='defense-propose':emit(propose_defense(Path(a.project),bug_id=a.bug_id,description=a.description,evidence=a.evidence,affected=[x.strip() for x in a.affected.split(',') if x.strip()]));return
 if a.cmd=='defense-promote':emit(promote_defense(Path(a.project),a.bug_id,verification_ref=a.verification_ref,human_approved=a.approved));return
 if a.cmd=='empirical-benchmark':
  raw=json.loads(Path(a.profiles).read_text(encoding='utf-8')); rows=raw.get('profiles',raw) if isinstance(raw,dict) else raw; profiles=[BenchmarkProfile(str(x['name']),tuple(str(c) for c in x['command']),{str(k):str(v) for k,v in x.get('env',{}).items()} or None) for x in rows];emit(compare_profiles(profiles,load_benchmark(Path(a.benchmark))));return
 if a.cmd=='v5-score':emit(v5_flagship_score(Path(__file__).resolve().parent));return
 if a.cmd=='v5-stress-suite':emit(v5_stress_suite());return
 if a.cmd=='target-10':emit(target10_gate(Path(a.project),run_reproducible_build=a.reproducible_build,probe_docker=a.probe_docker,require_certification=a.require_certification));return
 if a.cmd=='source-fingerprint':emit({'status':'pass',**repository_fingerprint(Path(a.project))});return
 if a.cmd=='polyglot-smoke':emit(run_polyglot_smoke());return
 if a.cmd=='runtime-policy':
  p=hardened_container_policy(a.risk,a.image,network_required=a.network_required,workspace_read_only=a.workspace_read_only);emit({'status':'pass','policy':p.to_dict()});return
 if a.cmd=='runtime-attestation-validate':emit(validate_runtime_attestation(json.loads(Path(a.file).read_text(encoding='utf-8')),a.risk));return
 if a.cmd=='attestation-contract':emit(release_attestation_contract());return
 if a.cmd=='attestation-validate':emit(validate_release_attestation(json.loads(Path(a.file).read_text(encoding='utf-8'))));return
 if a.cmd=='benchmark-v3-write':emit(write_target_corpus(Path(a.path),a.count));return
 if a.cmd=='benchmark-v3-validate':emit(validate_target_corpus(Path(a.path),a.minimum));return
 root=Path(getattr(a,'project','.')).expanduser().resolve()
 table={'inspect':inspect_project,'security':scan_project,'architecture':architecture_scan,'clean':scan_clean_code,'design':scan_design,'duplicates':scan_semantic_duplicates,'tests-quality':scan_test_quality,'genome-validate':validate_genome,'invariants-verify':verify_invariant_coverage,'bootstrap':bootstrap_project,'genome-init':init_genome,'state':load_state,'gate':project_gate,'platforms':adapter_report,'production-check':validate_production_ops,'production-init':lambda r:{'status':'pass','path':str(init_production_ops(r))},'ledger-verify':lambda r:EvidenceLedger(r).verify(),'flutter-stack-status':official_stack_status,'skills-lock':lock_skills,'supply-chain':lambda r:scan_supply_chain(r,False),'store-delivery-check':validate_store_delivery,'standards-status':standards_status,'technology-radar':technology_radar,'fabric-status':fabric_status,'contracts-check':contract_status,'release-plan':release_plan}
 if a.cmd in table:emit(table[a.cmd](root));return
 if a.cmd=='standards-init':emit({'status':'pass','path':str(init_standards_radar(root,a.force))});return
 if a.cmd=='knowledge-graph':emit({'status':'pass','path':str(write_project_graph(root)),'graph':build_project_graph(root)} if a.write else build_project_graph(root));return
 if a.cmd=='release-graph-init':emit({'status':'pass','path':str(init_release_graph(root,a.force))});return
 if a.cmd=='worker-register':
  cap=WorkerCapability(a.id,a.host,tuple(x.strip() for x in a.providers.split(',') if x.strip()),tuple(x.strip() for x in a.platforms.split(',') if x.strip()),a.max_risk.upper(),a.slots);emit({'status':'pass','worker':WorkerRegistry(root).register(cap)});return
 if a.cmd=='worker-select':emit(WorkerRegistry(root).select(risk=a.risk.upper(),platform=a.platform,provider=a.provider));return
 if a.cmd=='worker-reserve':emit(WorkerRegistry(root).reserve(risk=a.risk.upper(),platform=a.platform,provider=a.provider,task_id=a.task_id,owner=a.owner,slots=a.slots,ttl_seconds=a.ttl_seconds));return
 if a.cmd=='worker-release':emit(WorkerRegistry(root).release(a.reservation_id,owner=a.owner));return
 if a.cmd=='worker-status':emit(WorkerRegistry(root).status());return
 if a.cmd=='event-chain-verify':emit(Scheduler(root).verify_event_chain());return
 if a.cmd=='task-replay':emit(Scheduler(root).replay_task(a.task_id));return
 if a.cmd=='semantic-graph':emit(semantic_project_graph(root,include_authoritative=not a.fallback_only));return
 if a.cmd=='flutter-intelligence':emit(flutter_specialist_snapshot(root));return
 if a.cmd=='symbol-impact':emit(symbol_impact(root,a.symbol));return
 if a.cmd=='security-posture':emit(security_posture(root,release=a.release));return
 if a.cmd=='ci-plan':emit(build_ci_plan(root,a.profile));return
 if a.cmd=='release-control-status':emit(ReleaseController(root,a.release_id).status());return
 if a.cmd=='release-control-proof':emit(ReleaseController(root,a.release_id).set_proof(a.status));return
 if a.cmd=='release-control-approve':emit(ReleaseController(root,a.release_id).approve_production(approved=a.approved,actor=a.actor));return
 if a.cmd=='release-control-health':
  samples=json.loads(Path(a.file).read_text(encoding='utf-8')); windows=samples if isinstance(samples,list) else samples.get('windows',[]);ev=evaluate_health(HealthPolicy(),windows);emit(ReleaseController(root,a.release_id).record_health(a.stage,ev));return
 if a.cmd=='release-control-transition':emit(ReleaseController(root,a.release_id).transition(a.state,reason=a.reason));return
 if a.cmd=='model-route':emit(route_model(root,task_class=a.task_class,risk=a.risk,candidates=[x.strip() for x in a.candidates.split(',') if x.strip()] or None,minimum_samples=a.minimum_samples));return
 if a.cmd=='model-record':emit(record_model_outcome(root,task_class=a.task_class,model=a.model,accepted=a.accepted,cost_usd=a.cost_usd,seconds=a.seconds,tokens=a.tokens,security_failure=a.security_failure,architecture_failure=a.architecture_failure,proof_ref=a.proof_ref));return
 if a.cmd=='security-assurance':emit(run_security_assurance(root,a.release));return
 if a.cmd=='create':emit(create_project(root,a.org,a.platforms))
 elif a.cmd=='context':emit(context_for_task(root,a.task,a.limit))
 elif a.cmd=='risk':emit(classify_risk(a.task,a.files,a.call_sites).to_dict())
 elif a.cmd=='blast':emit(blast_radius(root,a.symbol))
 elif a.cmd=='plan':
  try:emit(ComponentRegistry().resolve([x.strip() for x in a.components.split(',') if x.strip()]))
  except ComponentError as e:emit({'status':'error','error':str(e)});raise SystemExit(2)
 elif a.cmd=='verify':emit(verify_project(root,a.profile))
 elif a.cmd=='score':emit(release_score(verify_project(root,a.profile),evidence=load_evidence_dir(root)))
 elif a.cmd=='capability-resolve':emit(resolve_intent(root,a.intent))
 elif a.cmd=='capability-add':emit(register_capability(root,a.id,a.owner,[x.strip() for x in a.provides.split(',') if x.strip()]))
 elif a.cmd=='invariant-add':emit(register_invariant(root,a.id,a.statement,a.owner,[x.strip() for x in a.tests.split(',') if x.strip()]))
 elif a.cmd=='intent-check':emit(validate_change_intent(root,Path(a.file) if a.file else None))
 elif a.cmd=='task-create':emit(create_task(root,a.title,a.risk,[x.strip() for x in a.depends_on.split(',') if x.strip()]))
 elif a.cmd=='schedule-create':emit(Scheduler(root).create_task(a.title,a.risk,[x.strip() for x in a.depends_on.split(',') if x.strip()],a.max_attempts))
 elif a.cmd=='schedule-ready':emit(Scheduler(root).ready(a.task_id))
 elif a.cmd=='schedule-claim':emit(Scheduler(root).claim_next(a.worker,a.lease_seconds))
 elif a.cmd=='components-solve':emit(solve_components([x.strip() for x in a.components.split(',') if x.strip()],[x.strip() for x in a.platforms.split(',') if x.strip()],a.max_risk))
 elif a.cmd=='task-transition':emit(transition(root,a.task_id,a.state,{'proof_status':a.proof_status,'review_blockers':a.review_blockers}))
 elif a.cmd=='proof':
  v=verify_project(root,a.profile);risk=classify_risk(a.task).to_dict();proof=build_proof(root,a.task_id,a.task,risk,v,evidence=load_evidence_dir(root));p=write_proof(root,proof);emit({'path':str(p),'validation':validate_proof(root,proof),'proof':proof})
 elif a.cmd=='store-delivery-init':emit({'status':'pass','path':str(init_store_delivery(root,a.force))})
 elif a.cmd=='store-delivery-preflight':emit(store_delivery_preflight(root,a.platform))
 elif a.cmd=='store-delivery-execute':emit(execute_store_delivery(root,a.platform,a.approved))
 elif a.cmd=='lifecycle-run':
  executor=UnifiedLifecycleExecutor.default(model=a.model,api_key=a.api_key,base_url=a.base_url,preferred=a.provider)
  emit(LifecycleRunner(root,executor).run_next(a.worker))
 elif a.cmd=='lifecycle-approve':
  if not a.approved: emit({'status':'blocked','reason':'--approved is required and Antigravity hook should request explicit user approval'});raise SystemExit(2)
  emit(LifecycleRunner(root,UnifiedLifecycleExecutor.default()).approve_high_risk(a.task_id))
 elif a.cmd=='delivery-init':emit(install_delivery_plane(root,a.force))
 elif a.cmd=='product-init':emit(write_product_definition(root,a.brief))
 elif a.cmd=='adr':emit(create_adr(root,a.title,a.context,a.decision,a.consequences))
if __name__=='__main__':main()
