import unittest
from flutter_foundry.score import release_score
class T(unittest.TestCase):
 def base(self):
  names=['dart_format','flutter_analyze','flutter_test','foundry_architecture','foundry_security']
  return {'checks':[{'name':n,'status':'pass'} for n in names],'blocking':[],'test_quality':{'status':'pass'},'clean_code':{'status':'pass'},'duplicate_guard':{'status':'pass'}}
 def test_booleans_do_not_get_credit(self):
  self.assertLess(release_score(self.base(),runtime_evidence=True,accessibility_evidence=True,performance_evidence=True)['score'],100)
 def test_all_valid_evidence_can_score_100(self):
  kinds=['acceptance','performance','accessibility','runtime','supply_chain','operability','cost'];ev=[{'schema':'foundry/evidence/v1','kind':k,'result':'PASS','timestamp':'x','commit':'abc','metadata':{}} for k in kinds]
  self.assertEqual(release_score(self.base(),evidence=ev)['score'],100)
