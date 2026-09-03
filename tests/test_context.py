import tempfile, unittest
from pathlib import Path
from flutter_foundry.context_engine import context_for_task

class ContextTest(unittest.TestCase):
    def test_ranks_matching_feature(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"lib/features/workout").mkdir(parents=True); (root/"lib/features/profile").mkdir(parents=True)
            (root/"lib/features/workout/history.dart").write_text('class WorkoutHistoryPagination {}')
            (root/"lib/features/profile/page.dart").write_text('class ProfilePage {}')
            out=context_for_task(root,"fix workout history pagination",5)
            self.assertEqual(out["files"][0]["path"],"lib/features/workout/history.dart")

if __name__ == "__main__": unittest.main()
