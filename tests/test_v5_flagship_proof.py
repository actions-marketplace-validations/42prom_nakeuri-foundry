import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flutter_foundry.antigravity_native import install_antigravity_team,native_team_status
from flutter_foundry.bootstrap import bootstrap_project
from flutter_foundry.defense_memory import promote_defense,propose_defense
from flutter_foundry.empirical_benchmark import BenchmarkProfile,ablation_report,compare_profiles
from flutter_foundry.native_e2e import patrol_status
from flutter_foundry.requirements import compile_requirements
from flutter_foundry.runtime_provider import AntigravityHeadlessProvider,KubernetesJobProvider
from flutter_foundry.team import native_role_plan
from flutter_foundry.v5_maturity import v5_flagship_score

class V5FlagshipTests(unittest.TestCase):
    def test_specification_v2_has_explicit_negative_nfr_and_oracles(self):
        out=compile_requirements('Add secure subscription payment login with offline retry and push notifications.')
        spec=out['executable_specification']
        self.assertEqual(spec['schema'],'nakeuri/executable-specification/v2')
        self.assertTrue(spec['requirements']);self.assertTrue(spec['negative_cases']);self.assertTrue(spec['non_functional_requirements'])
        self.assertEqual(len(spec['oracle_ids']),len(set(spec['oracle_ids'])))
        self.assertTrue(spec['coverage_contract']['high_risk_test_oracles_are_independent_from_implementation_worker'])

    def test_antigravity_native_team_is_installed_with_read_only_reviewers(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/'pubspec.yaml').write_text('name: x\n')
            install_antigravity_team(r);st=native_team_status(r);self.assertEqual(st['status'],'pass')
            reviewer=(r/'.agents/agents/nakeuri-security-reviewer.md').read_text()
            self.assertIn('model: pro',reviewer);self.assertNotIn('replace_file_content',reviewer);self.assertIn('commandExecutionPolicy: sandbox',reviewer)
            worker=(r/'.agents/agents/nakeuri-flutter-worker.md').read_text();self.assertIn('replace_file_content',worker)
            plan=native_role_plan('HIGH');self.assertIn('security-reviewer',plan['roles']);self.assertTrue(plan['workspace_policy']['high_risk_oracle_independent'])

    def test_bootstrap_installs_native_team(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/'pubspec.yaml').write_text('name: x\n')
            out=bootstrap_project(r,install_delivery=False);self.assertEqual(out['native_team']['status'],'pass');self.assertTrue((r/'.agents/agents/nakeuri-merge-arbiter.md').exists())

    def test_antigravity_headless_provider_uses_native_agent_and_structured_review(self):
        provider=AntigravityHeadlessProvider()
        envelope={"status":"SUCCESS","response":"{}","duration_seconds":2,"num_turns":1,"usage":{"total_tokens":42},"conversation_id":"c","structured_output":{"schema":"nakeuri/review-output/v1","status":"PASS","findings":[]}}
        import subprocess as _sp
        completed=_sp.CompletedProcess(["agy"],0,stdout=json.dumps(envelope),stderr="")
        with tempfile.TemporaryDirectory() as d, patch('flutter_foundry.runtime_provider.shutil.which',return_value='/usr/bin/agy'), patch('flutter_foundry.runtime_provider.subprocess.run',return_value=completed) as run:
            out=provider.run_agent(Path(d),'security-reviewer','review',risk='MEDIUM')
            self.assertEqual(out['status'],'completed');self.assertEqual(out['output']['status'],'PASS');self.assertEqual(out['usage']['tokens'],42)
            cmd=run.call_args.args[0];self.assertIn('--agent',cmd);self.assertIn('nakeuri-security-reviewer',cmd);self.assertIn('--json-schema',cmd);self.assertIn('--sandbox',cmd)
        self.assertEqual(provider.run_agent(Path('.'),'worker','x',risk='HIGH')['status'],'blocked')

    def test_kubernetes_manifest_is_hardened_and_network_denied(self):
        p=KubernetesJobProvider(image='example.invalid/agent@sha256:'+'a'*64,command=['agent'])
        docs=p._manifest('nakeuri-test','e30=','HIGH');job,net=docs
        pod=job['spec']['template']['spec'];c=pod['containers'][0]
        self.assertTrue(pod['securityContext']['runAsNonRoot']);self.assertFalse(pod['automountServiceAccountToken']);self.assertFalse(c['securityContext']['allowPrivilegeEscalation'])
        self.assertEqual(c['securityContext']['capabilities']['drop'],['ALL']);self.assertEqual(net['spec']['egress'],[])

    def test_patrol_status_distinguishes_configured_but_unavailable(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/'pubspec.yaml').write_text('name: x\ndev_dependencies:\n  patrol: any\n')
            with patch('flutter_foundry.native_e2e.shutil.which',return_value=None):
                out=patrol_status(r);self.assertTrue(out['configured']);self.assertEqual(out['status'],'unavailable')

    def test_defect_promotion_requires_verification_and_policy_approval(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);p=propose_defense(r,bug_id='BUG-1',description='authorization tenant leak',evidence='repro')
            self.assertEqual(p['defense_kind'],'security-invariant')
            self.assertEqual(promote_defense(r,'BUG-1',verification_ref='')['status'],'blocked')
            self.assertEqual(promote_defense(r,'BUG-1',verification_ref='proof-1')['status'],'blocked')
            self.assertEqual(promote_defense(r,'BUG-1',verification_ref='proof-1',human_approved=True)['status'],'pass')

    def test_empirical_benchmark_hides_acceptance_and_enforces_budget(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);repo=base/'repo';repo.mkdir();subprocess.run(['git','init','-q'],cwd=repo,check=True);subprocess.run(['git','config','user.email','x@y.invalid'],cwd=repo,check=True);subprocess.run(['git','config','user.name','X'],cwd=repo,check=True)
            (repo/'v.txt').write_text('bad\n');subprocess.run(['git','add','.'],cwd=repo,check=True);subprocess.run(['git','commit','-qm','base'],cwd=repo,check=True)
            runner=base/'runner.py';runner.write_text('import json,sys\nfrom pathlib import Path\nr=json.loads(Path(sys.argv[1]).read_text());Path(r["workspace"]).joinpath("v.txt").write_text("good\\n");Path(sys.argv[2]).write_text(json.dumps({"status":"completed","usage":{"tokens":10,"cost_usd":0.1}}))\n')
            check=base/'check.py';check.write_text('from pathlib import Path\nimport sys\nsys.exit(0 if Path("v.txt").read_text().strip()=="good" else 1)\n')
            prof=BenchmarkProfile('p',(sys.executable,str(runner),'{request}','{response}'))
            task={'id':'T','repo':str(repo),'prompt':'fix','hidden_acceptance':[{'name':'h','command':[sys.executable,str(check)]}],'token_budget':100,'cost_budget_usd':1}
            out=compare_profiles([prof],[task]);self.assertEqual(out['summary']['p']['accepted'],1);self.assertTrue(out['results'][0]['fairness']['hidden_acceptance_not_sent_to_runner'])

    def test_ablation_report_uses_empirical_summary_deltas(self):
        comparison={"summary":{"base":{"acceptance_rate":0.5,"total_cost_usd":2,"total_tokens":100,"median_duration_ms":1000},"full":{"acceptance_rate":0.75,"total_cost_usd":1.8,"total_tokens":90,"median_duration_ms":900}}}
        out=ablation_report(comparison,'base');self.assertEqual(out['profiles']['full']['acceptance_delta_pp'],25.0);self.assertLess(out['profiles']['full']['cost_delta_usd'],0)

    def test_foundry_cache_and_parallel_map(self):
        from flutter_foundry.cache import FoundryCache, parallel_map
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            cache = FoundryCache(root)
            self.assertIsNone(cache.get('test', root, 'fp1'))
            cache.set('test', root, 'fp1', {'cached': True})
            self.assertEqual(cache.get('test', root, 'fp1'), {'cached': True})
            self.assertIsNone(cache.get('test', root, 'fp2'))
            res = parallel_map(lambda x: x * 2, [1, 2, 3])
            self.assertEqual(res, [2, 4, 6])

    def test_surgical_auto_remediation(self):
        from flutter_foundry.remediation import scan_and_remediate
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / '.gitignore').write_text('node_modules\n', encoding='utf-8')
            res = scan_and_remediate(root, apply=True)
            self.assertEqual(res['status'], 'remediated')
            self.assertTrue((root / '.foundry' / 'evidence').is_dir())
            self.assertIn('.nakeuri/cache', (root / '.gitignore').read_text(encoding='utf-8'))

    def test_v5_score_is_full_implementation_coverage(self):
        import flutter_foundry
        package=Path(flutter_foundry.__file__).resolve().parent
        out=v5_flagship_score(package);self.assertEqual(out['status'],'pass');self.assertEqual(out['score'],10.0)

if __name__=='__main__':unittest.main()
