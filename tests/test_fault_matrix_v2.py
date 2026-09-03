import unittest
from flutter_foundry.fault_matrix import build_fault_matrix
class T(unittest.TestCase):
 def test_auth_payment_high_has_relevant_failures(self):
  x=build_fault_matrix('refresh auth token after subscription payment','HIGH');self.assertIn('refresh-failure',x['scenarios']);self.assertIn('duplicate-event',x['scenarios']);self.assertEqual(x['required_evidence'],'runtime+integration')
 def test_low_does_not_explode_matrix(self):
  self.assertLessEqual(len(build_fault_matrix('simple local button','LOW')['scenarios']),4)
