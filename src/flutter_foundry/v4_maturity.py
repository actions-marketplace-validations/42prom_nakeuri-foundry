from __future__ import annotations
from pathlib import Path
from typing import Any


def _contains(p: Path,name: str,*needles: str)->bool:
    try:text=(p/name).read_text(encoding='utf-8')
    except Exception:return False
    return all(n in text for n in needles)


def v4_hardening_score(package_dir: Path)->dict[str,Any]:
    p=package_dir.resolve()
    criteria={
      'execution':[('unified provider runtime',_contains(p,'runtime_provider.py','UnifiedLifecycleExecutor','validate_provider_result')),('docker JSON agent provider',_contains(p,'runtime_provider.py','DockerJsonAgentProvider','hardened_container_policy')),('risk isolation routing',_contains(p,'runtime_provider.py','no available provider satisfies risk and isolation requirements')),('lifecycle provider-neutral call',_contains(p,'lifecycle.py','_execute_agent','run_task')),('provider proof obligations',_contains(p,'runtime_provider.py','provider_contract','missing_obligations'))],
      'semantics':[('stdio JSON-RPC LSP client',_contains(p,'lsp_semantics.py','Content-Length','textDocument/documentSymbol')),('Dart LSP',_contains(p,'lsp_semantics.py','dart','language-server')),('TypeScript/Pyright',_contains(p,'lsp_semantics.py','typescript-language-server','pyright-langserver')),('Go/Rust/Java LSP',_contains(p,'lsp_semantics.py','gopls','rust-analyzer','jdtls')),('semantic graph consumes live LSP',_contains(p,'semantic_engine.py','authoritative_semantic_snapshot','authoritative-lsp'))],
      'flutter':[('Flutter specialist snapshot',_contains(p,'flutter_intelligence.py','flutter_specialist_snapshot')),('state-management awareness',_contains(p,'flutter_intelligence.py','riverpod','bloc','ChangeNotifier')),('navigation awareness',_contains(p,'flutter_intelligence.py','GoRoute')),('async BuildContext guard',_contains(p,'flutter_intelligence.py','async-build-context','context.mounted')),('platform-channel awareness',_contains(p,'flutter_intelligence.py','MethodChannel','EventChannel'))],
      'reliability':[('scheduler lease fencing + lifecycle heartbeat',_contains(p,'scheduler.py','lease_token','stale lease fencing token') and _contains(p,'lifecycle.py','_execute_worker_with_heartbeat','scheduler.heartbeat')),('schema migration v4',_contains(p,'scheduler.py','SCHEMA_VERSION = 4','version < 4')),('provider availability is observed',_contains(p,'runtime_provider.py','available()','risk_allowed')),('high-risk weak isolation blocked',_contains(p,'runtime_provider.py','isolation_allowed','HIGH')),('provider result contract gate',_contains(p,'runtime_provider.py','runtime provider proof obligations not satisfied'))],
      'routing':[('verified outcome recording + Wilson lower confidence',_contains(p,'model_router.py','record_model_outcome','_wilson_lower','acceptance_lower_95')),('risk-specific quality band',_contains(p,'model_router.py','tolerance=0.005','HIGH')),('security/architecture failure routing',_contains(p,'model_router.py','security_failure_rate','architecture_failure_rate')),('independent high-risk verifier',_contains(p,'model_router.py','verification_model','requires_independent_model_review')),('budget remains enforced',_contains(p,'model_router.py','budget_policy','max_cost_usd'))],
    }
    out={};passed=total=0
    for category,rows in criteria.items():
        ok=sum(1 for _,v in rows if v);n=len(rows);passed+=ok;total+=n;out[category]={'score':round(10*ok/n,2),'passed':ok,'total':n,'criteria':[{'name':name,'pass':v} for name,v in rows]}
    return {'status':'pass' if passed==total else 'partial','schema':'nakeuri/v4-hardening-score/v1','score':round(10*passed/total,2),'passed':passed,'total':total,'categories':out,'claim_boundary':'This measures repository implementation coverage of V4 hardening, not live production or peer superiority.'}
