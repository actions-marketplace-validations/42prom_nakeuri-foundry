import json
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from flutter_foundry.attestation import validate_release_attestation
from flutter_foundry.benchmark_v3 import generate_target_corpus, validate_target_corpus, write_target_corpus
from flutter_foundry.ci_plan import build_ci_plan
from flutter_foundry.distributed_runtime import WorkerCapability, WorkerRegistry
from flutter_foundry.docker_runtime import DockerExecutor
from flutter_foundry.mcp_gateway import MCPServerPolicy, authorize_request, validate_list_cache
from flutter_foundry.model_router import route_model
from flutter_foundry.release_controller import HealthPolicy, ReleaseController, evaluate_health
from flutter_foundry.runtime_security import hardened_container_policy, validate_runtime_attestation
from flutter_foundry.scheduler import Scheduler
from flutter_foundry.security_posture import security_posture
from flutter_foundry.semantic_engine import semantic_project_graph


class Target10Tests(unittest.TestCase):
    def test_atomic_worker_capacity_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); reg=WorkerRegistry(root)
            reg.register(WorkerCapability('w1','host',('docker',),('flutter',),'RELEASE',cpu_slots=4),ttl_seconds=120)
            results=[]; lock=threading.Lock()
            def claim(i):
                r=reg.reserve(risk='HIGH',platform='flutter',provider='docker',task_id=f'TASK-{i}',owner=f'o{i}',slots=1)
                with lock: results.append(r)
            threads=[threading.Thread(target=claim,args=(i,)) for i in range(12)]
            for t in threads:t.start()
            for t in threads:t.join()
            self.assertEqual(sum(r['status']=='pass' for r in results),4)
            self.assertEqual(len({r['reservation_id'] for r in results if r['status']=='pass'}),4)
            self.assertEqual(reg.schema_status()['status'],'pass')

    def test_scheduler_events_are_tamper_evident_and_replayable(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); s=Scheduler(root)
            task=s.create_task('x',task_id='TASK-X'); s.ready(task['id']); s.claim_next('w')
            self.assertEqual(s.verify_event_chain()['status'],'pass')
            self.assertGreaterEqual(s.replay_task('TASK-X')['count'],3)
            con=sqlite3.connect(s.path); con.execute("UPDATE events SET payload='{}' WHERE seq=1"); con.commit(); con.close()
            self.assertEqual(s.verify_event_chain()['status'],'fail')

    def test_high_container_requires_digest_and_runtime_proof(self):
        with self.assertRaises(ValueError):
            hardened_container_policy('HIGH','python:3.12-slim')
        image='repo/image@sha256:'+'a'*64
        p=hardened_container_policy('HIGH',image)
        good={'image':image,'user':'65532:65532','read_only_rootfs':True,'cap_drop_all':True,'no_new_privileges':True,'network_mode':'none','memory_mb':4096,'cpus':2}
        self.assertEqual(validate_runtime_attestation(good,'HIGH')['status'],'pass')
        bad={**good,'user':'0:0'}
        self.assertEqual(validate_runtime_attestation(bad,'HIGH')['status'],'fail')

    def test_docker_executor_validates_observed_config(self):
        image='repo/image@sha256:'+'b'*64
        policy=hardened_container_policy('HIGH',image)
        inspect=[{'Image':image,'Config':{'Image':image,'User':'65532:65532'},'HostConfig':{'ReadonlyRootfs':True,'CapDrop':['ALL'],'SecurityOpt':['no-new-privileges:true'],'NetworkMode':'none','Memory':4096*1024*1024,'NanoCpus':2_000_000_000,'PidsLimit':384}}]
        def runner(argv,**kwargs):
            if argv[:2]==['docker','create']: return subprocess.CompletedProcess(argv,0,'cid\n','')
            if argv[:2]==['docker','inspect'] and '--format' not in argv: return subprocess.CompletedProcess(argv,0,json.dumps(inspect),'')
            if argv[:2]==['docker','start']: return subprocess.CompletedProcess(argv,0,'ok','')
            if argv[:3]==['docker','inspect','--format']: return subprocess.CompletedProcess(argv,0,json.dumps({'ExitCode':0}),'')
            if argv[:2]==['docker','rm']: return subprocess.CompletedProcess(argv,0,'','')
            raise AssertionError(argv)
        with tempfile.TemporaryDirectory() as d:
            r=DockerExecutor(runner=runner).execute(policy,Path(d),['python','-V'])
            self.assertEqual(r['status'],'pass'); self.assertEqual(r['security']['status'],'pass')

    def test_semantic_graph_spans_polyglot_sources(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); (r/'api').mkdir();(r/'web').mkdir();(r/'mobile').mkdir()
            (r/'api'/'pyproject.toml').write_text('[project]\nname="x"\nversion="0"\n')
            (r/'api'/'app.py').write_text('import json\nclass UserService: pass\ndef run(): pass\n')
            (r/'web'/'package.json').write_text('{"dependencies":{"next":"16"},"scripts":{"build":"next build"}}')
            (r/'web'/'page.tsx').write_text("import x from './x'; export function Page(){return null}")
            (r/'mobile'/'pubspec.yaml').write_text('name: x\n')
            (r/'mobile'/'a.dart').write_text("import 'package:flutter/widgets.dart'; class A {}")
            g=semantic_project_graph(r)
            self.assertEqual(g['status'],'pass')
            self.assertTrue({'python','typescript','dart'}.issubset(set(g['language_file_counts'])))
            self.assertGreater(len(g['nodes']),5)

    def test_release_controller_requires_proof_approval_and_health(self):
        policy=HealthPolicy(min_sample_count=10,required_consecutive_windows=2)
        windows=[{'sample_count':100,'error_rate':0,'crash_free_sessions':1,'p95_latency_ms':100} for _ in range(2)]
        health=evaluate_health(policy,windows); self.assertEqual(health['status'],'pass')
        with tempfile.TemporaryDirectory() as d:
            c=ReleaseController(Path(d),'REL-1')
            self.assertEqual(c.transition('STAGING')['status'],'blocked')
            c.set_proof('PASS'); self.assertEqual(c.transition('STAGING')['state'],'STAGING')
            self.assertEqual(c.transition('CANARY')['state'],'CANARY')
            self.assertEqual(c.transition('PRODUCTION')['status'],'blocked')
            c.record_health('canary',health); c.approve_production(approved=True,actor='human')
            self.assertEqual(c.transition('PRODUCTION')['state'],'PRODUCTION')
            self.assertEqual(c.transition('VERIFIED')['status'],'blocked')
            c.record_health('production',health); self.assertEqual(c.transition('VERIFIED')['state'],'VERIFIED')

    def test_release_attestation_requires_external_trust(self):
        base={'artifact_sha256':'a'*64,'sbom_sha256':'b'*64,'source_commit':'c'*40,'builder_identity':'github:repo/workflow','provenance_verified':True,'signature_verified':True,'slsa_build_level':'L2'}
        self.assertEqual(validate_release_attestation(base)['status'],'fail')
        good={**base,'transparency_log_verified':True}
        self.assertEqual(validate_release_attestation(good)['status'],'pass')

    def test_mcp_stateless_routing_and_issuer_validation(self):
        p=MCPServerPolicy('docs','official',allowed_tools=('search',),auth_issuer='https://issuer.example',require_auth=True,allowed_methods=('tools/call',))
        ok=authorize_request(p,method='tools/call',name='search',headers={'Mcp-Method':'tools/call','Mcp-Name':'search'},auth={'issuer':'https://issuer.example'})
        self.assertEqual(ok['status'],'pass')
        self.assertEqual(authorize_request(p,method='tools/call',name='search',headers={'Mcp-Method':'bad'},auth={'issuer':'https://issuer.example'})['status'],'blocked')
        self.assertEqual(validate_list_cache(p,1000,deterministic_order=True)['status'],'pass')

    def test_security_posture_maps_current_control_families(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); (r/'pubspec.yaml').write_text('name: x\n')
            s=security_posture(r,release=True)
            self.assertIn('OWASP MASVS',s['standards']['mobile']['standard'])
            self.assertEqual(s['standards']['supply_chain']['version'],'1.2 approved')
            self.assertIn('cosign',[t['id'] for t in s['tools']])

    def test_target_benchmark_has_500_controlled_scenarios(self):
        rows=generate_target_corpus(500); self.assertEqual(len(rows),500)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'tasks.jsonl'; write_target_corpus(p,500)
            v=validate_target_corpus(p); self.assertEqual(v['status'],'pass');self.assertEqual(v['count'],500)

    def test_model_router_prefers_near_best_lower_cost_from_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); p=r/'.factory/benchmarks/model-performance.jsonl';p.parent.mkdir(parents=True)
            rows=[]
            for _ in range(20): rows.append({'task_class':'flutter-bug','model':'A','accepted':True,'cost_usd':1,'seconds':20,'tokens':1000})
            for _ in range(20): rows.append({'task_class':'flutter-bug','model':'B','accepted':True,'cost_usd':.2,'seconds':10,'tokens':500})
            p.write_text('\n'.join(json.dumps(x) for x in rows)+'\n')
            result=route_model(r,task_class='flutter-bug',risk='MEDIUM')
            self.assertEqual(result['status'],'pass');self.assertEqual(result['selection'],'B')

    def test_release_ci_refuses_unlocked_node_dependencies(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/'package.json').write_text('{"dependencies":{"next":"16"},"scripts":{"build":"next build"}}')
            self.assertEqual(build_ci_plan(r,'release')['status'],'fail')
            (r/'package-lock.json').write_text('{}')
            self.assertEqual(build_ci_plan(r,'release')['status'],'pass')

if __name__=='__main__': unittest.main()
