import json,tempfile,unittest
from pathlib import Path
from flutter_foundry.benchmark import summarize_results,compare_runs
class T(unittest.TestCase):
    def test_richer_metrics_and_comparison(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a';b=Path(d)/'b';a.write_text(json.dumps({'accepted':False,'cost':2,'repair_iterations':2,'tokens':100,'seconds':10,'escaped_regressions':1})+'\n');b.write_text(json.dumps({'accepted':True,'cost':1,'repair_iterations':0,'tokens':80,'seconds':8,'escaped_regressions':0})+'\n')
            self.assertEqual(summarize_results(b)['first_pass_rate'],1.0);self.assertTrue(compare_runs(a,b)['delta']['acceptance_rate']['better'])
    def test_golden_corpus_has_60_tasks(self):
        p=Path(__file__).parents[1]/'evals/golden_tasks/core.jsonl';self.assertEqual(len([x for x in p.read_text().splitlines() if x]),60)
