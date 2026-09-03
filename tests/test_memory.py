import tempfile, unittest
from pathlib import Path
from flutter_foundry.memory import record_learning, query_learnings

class MemoryTest(unittest.TestCase):
    def test_append_and_query(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            record_learning(root,"false_positive","gallery permission","camera-only callsite","check ImageSource.gallery before flagging",["permission"])
            out=query_learnings(root,["gallery"])
            self.assertEqual(len(out),1)
            self.assertEqual(out[0]["kind"],"false_positive")

if __name__ == "__main__": unittest.main()
