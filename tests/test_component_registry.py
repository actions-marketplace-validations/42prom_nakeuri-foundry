import unittest
from flutter_foundry.component_registry import ComponentRegistry

class ComponentRegistryTest(unittest.TestCase):
    def test_auth_resolves_network_and_storage(self):
        plan = ComponentRegistry().resolve(["auth-session"])
        ids = plan["ordered_components"]
        self.assertIn("network-dio", ids)
        self.assertIn("secure-storage", ids)
        self.assertLess(ids.index("network-dio"), ids.index("auth-session"))
        self.assertLess(ids.index("secure-storage"), ids.index("auth-session"))

if __name__ == "__main__": unittest.main()
