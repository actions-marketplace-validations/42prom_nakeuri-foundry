import json
import os
import sqlite3
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from flutter_foundry.flutter_intelligence import flutter_specialist_snapshot
from flutter_foundry.lsp_semantics import LSPClient
from flutter_foundry.model_router import route_model
from flutter_foundry.runtime_provider import CallbackProvider, ProviderCapabilities, UnifiedLifecycleExecutor
from flutter_foundry.scheduler import Scheduler


class V4ExecutionIntelligenceTests(unittest.TestCase):
    def test_unified_runtime_rejects_weak_high_risk_and_selects_container(self):
        def weak(**kwargs):
            return {"status":"completed","usage":{},"provider_evidence":{"commit_bound_workspace":True,"structured_execution_result":True,"usage_telemetry":True}}
        strong_evidence={
            "commit_bound_workspace":True,"structured_execution_result":True,"usage_telemetry":True,
            "security_isolation_attestation":True,"network_policy_attestation":True,"resource_limit_attestation":True,"non_root_attestation":True,
            "ephemeral_environment":True,"supply_chain_identity":True,"human_approval_boundary":True,
        }
        def strong(**kwargs):
            return {"status":"completed","usage":{},"provider_evidence":dict(strong_evidence)}
        runtime=UnifiedLifecycleExecutor([
            CallbackProvider(ProviderCapabilities("openhands","worktree","MEDIUM"),weak),
            CallbackProvider(ProviderCapabilities("docker","container","RELEASE",observed_runtime_attestation=True),strong),
        ])
        self.assertEqual(runtime.select("HIGH")["selection"],"docker")
        with tempfile.TemporaryDirectory() as d:
            out=runtime.run_task(Path(d),"worker","do work",risk="HIGH")
            self.assertEqual(out["status"],"completed")
            self.assertEqual(out["provider_contract"]["status"],"pass")

    def test_high_risk_blocks_when_only_worktree_provider_exists(self):
        p=CallbackProvider(ProviderCapabilities("openhands","worktree","MEDIUM"),lambda **kwargs:{"status":"completed"})
        runtime=UnifiedLifecycleExecutor([p])
        self.assertEqual(runtime.select("HIGH")["status"],"blocked")

    def test_runtime_status_does_not_report_pass_without_an_available_provider(self):
        p=CallbackProvider(ProviderCapabilities("openhands","worktree","MEDIUM"),lambda **kwargs:{"status":"completed"},availability=lambda:False)
        status=UnifiedLifecycleExecutor([p]).status()
        self.assertEqual(status["status"],"partial")
        self.assertEqual(status["available_providers"],0)

    def test_scheduler_lease_fencing_rejects_stale_completion(self):
        with tempfile.TemporaryDirectory() as d:
            s=Scheduler(Path(d));s.create_task("x",task_id="TASK-X");s.ready("TASK-X")
            first=s.claim_next("worker",30);old=first["lease_token"]
            con=sqlite3.connect(s.path);con.execute("UPDATE tasks SET lease_until='2000-01-01T00:00:00+00:00' WHERE id='TASK-X'");con.commit();con.close()
            s.recover_expired_leases();second=s.claim_next("worker",30);new=second["lease_token"]
            self.assertNotEqual(old,new)
            with self.assertRaisesRegex(ValueError,"stale lease fencing token"):
                s.finish_attempt("TASK-X","worker",True,lease_token=old)
            self.assertEqual(s.finish_attempt("TASK-X","worker",True,lease_token=new)["state"],"VERIFYING")

    def test_flutter_specialist_detects_state_routes_channels_and_async_context(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/"lib").mkdir()
            (r/"pubspec.yaml").write_text("name: x\ndependencies:\n  flutter_riverpod: any\n  go_router: any\n")
            (r/"lib"/"app.dart").write_text(textwrap.dedent("""
                final userProvider = Provider((ref) => 1);
                final route = GoRoute(path: '/home', builder: (context, state) => const Home());
                final channel = MethodChannel('app/native');
                Future<void> save(BuildContext context) async {
                  await Future<void>.delayed(Duration.zero);
                  Navigator.of(context).pop();
                }
            """))
            out=flutter_specialist_snapshot(r)
            self.assertEqual(out["status"],"pass")
            self.assertIn("riverpod",out["frameworks"]);self.assertIn("go_router",out["frameworks"])
            self.assertEqual(out["routes"][0]["path"],"/home")
            self.assertEqual(out["platform_channels"][0]["channel"],"app/native")
            self.assertGreaterEqual(out["risk_summary"]["async_context"],1)

    def test_lsp_client_queries_document_symbols_over_json_rpc(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);source=r/"a.py";source.write_text("def hello(): pass\n")
            server=r/"fake_lsp.py"
            server.write_text(textwrap.dedent(r'''
                import json,sys
                def read_msg():
                    headers={}
                    while True:
                        line=sys.stdin.buffer.readline()
                        if not line: return None
                        if line in (b'\r\n',b'\n'): break
                        k,v=line.decode().split(':',1);headers[k.lower().strip()]=v.strip()
                    n=int(headers['content-length']);return json.loads(sys.stdin.buffer.read(n))
                def send(obj):
                    body=json.dumps(obj,separators=(',',':')).encode();sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode()+body);sys.stdout.buffer.flush()
                while True:
                    m=read_msg()
                    if m is None: break
                    if 'id' not in m: continue
                    method=m.get('method')
                    if method=='initialize': send({'jsonrpc':'2.0','id':m['id'],'result':{'capabilities':{'documentSymbolProvider':True}}})
                    elif method=='textDocument/documentSymbol': send({'jsonrpc':'2.0','id':m['id'],'result':[{'name':'hello','kind':12,'selectionRange':{'start':{'line':0,'character':4},'end':{'line':0,'character':9}},'range':{'start':{'line':0,'character':0},'end':{'line':0,'character':20}}}]})
                    elif method=='shutdown': send({'jsonrpc':'2.0','id':m['id'],'result':None})
                    else: send({'jsonrpc':'2.0','id':m['id'],'result':None})
            '''))
            with LSPClient([sys.executable,str(server)],r,timeout=3) as client:
                rows=client.document_symbols(source,"python")
            self.assertEqual(rows[0]["name"],"hello")

    def test_high_risk_model_route_recommends_independent_verifier(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);p=r/".factory/benchmarks/model-performance.jsonl";p.parent.mkdir(parents=True)
            rows=[]
            for model,cost in (("A",1.0),("B",0.4)):
                for _ in range(40): rows.append({"task_class":"auth","model":model,"accepted":True,"cost_usd":cost,"seconds":10,"tokens":500})
            p.write_text("\n".join(json.dumps(x) for x in rows)+"\n")
            out=route_model(r,task_class="auth",risk="HIGH")
            self.assertEqual(out["selection"],"B")
            self.assertEqual(out["verification_model"],"A")
            self.assertTrue(out["requires_independent_model_review"])

if __name__ == "__main__":
    unittest.main()
