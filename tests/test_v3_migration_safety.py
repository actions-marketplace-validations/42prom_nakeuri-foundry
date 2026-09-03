import unittest
from flutter_foundry.migration_safety import assess_migration

class V3MigrationSafetyTests(unittest.TestCase):
    def test_breaking_schema_change_blocks_old_consumer(self):
        m={'operations':[{'op':'drop_column','field':'status'}],'backup_verified':True,'rollback_tested':True,'backward_compatible':False,'expand_contract':True}
        r=assess_migration(m,[{'id':'mobile-v1','fields':['status']}])
        self.assertEqual(r['status'],'fail'); self.assertTrue(any(f.get('consumer')=='mobile-v1' for f in r['findings']))
    def test_safe_additive_migration_passes(self):
        r=assess_migration({'operations':[{'op':'add_column','field':'nickname'}],'backward_compatible':True},[])
        self.assertEqual(r['status'],'pass')
