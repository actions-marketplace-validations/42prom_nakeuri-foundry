import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flutter_foundry.agent_runtime import ScriptedAgentExecutor
from flutter_foundry.assurance import verify_assurance_archive
from flutter_foundry.lifecycle import LifecycleRunner
from flutter_foundry.scheduler import Scheduler


def git(root: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=True)
    return p.stdout.strip()


class T(unittest.TestCase):
    def make_repo(self):
        td = tempfile.TemporaryDirectory(); root = Path(td.name)
        git(root, "init", "-b", "main")
        git(root, "config", "user.email", "test@example.com")
        git(root, "config", "user.name", "Test")
        (root / ".gitignore").write_text(".factory/\n", encoding="utf-8")
        (root / "README.md").write_text("base\n", encoding="utf-8")
        git(root, "add", "."); git(root, "commit", "-m", "base")
        return td, root

    def executor(self, isolation="container"):
        def callback(workspace, role, prompt, output_path):
            if role == "worker":
                (workspace / "feature.txt").write_text("implemented\n", encoding="utf-8")
                git(workspace, "add", "feature.txt")
                git(workspace, "commit", "-m", "feat: implement task")
                return {"status": "completed"}
            payload = {"schema": "nakeuri/review-output/v1", "status": "PASS", "findings": []}
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(payload), encoding="utf-8")
            return {"status": "completed", "output": payload}
        return ScriptedAgentExecutor(callback=callback, isolation_level=isolation)

    @patch("flutter_foundry.lifecycle.verify_project")
    def test_medium_runs_to_mergeable_with_portable_assurance(self, verify):
        verify.return_value = {"status": "pass", "blocking": [], "checks": []}
        td, root = self.make_repo()
        try:
            s = Scheduler(root)
            task = s.create_task("Implement feature", "MEDIUM")
            s.ready(task["id"])
            runner = LifecycleRunner(root, self.executor())
            result = runner.run_next("worker-1")
            self.assertEqual(result["status"], "mergeable")
            self.assertEqual(s.get(task["id"])["state"], "MERGEABLE")
            archive = Path(result["assurance"]["archive"])
            self.assertTrue(archive.is_file())
            self.assertEqual(verify_assurance_archive(archive)["status"], "pass")
            archived = {x["path"] for x in result["assurance"]["manifest"]["artifacts"]}
            self.assertTrue(any("verification-result.json" in x for x in archived))
        finally:
            td.cleanup()

    @patch("flutter_foundry.lifecycle.verify_project")
    def test_high_requires_human_approval_after_proof(self, verify):
        verify.return_value = {"status": "pass", "blocking": [], "checks": []}
        td, root = self.make_repo()
        try:
            s = Scheduler(root)
            task = s.create_task("Change authentication", "HIGH")
            s.ready(task["id"])
            runner = LifecycleRunner(root, self.executor("container"))
            result = runner.run_next("worker-1")
            self.assertEqual(result["status"], "awaiting_human_approval")
            self.assertEqual(s.get(task["id"])["state"], "REVIEWING")
            approved = runner.approve_high_risk(task["id"])
            self.assertEqual(approved["status"], "mergeable")
            self.assertEqual(s.get(task["id"])["state"], "MERGEABLE")
        finally:
            td.cleanup()

    @patch("flutter_foundry.lifecycle.verify_project")
    def test_high_worktree_only_executor_cannot_earn_strict_proof(self, verify):
        verify.return_value = {"status": "pass", "blocking": [], "checks": []}
        td, root = self.make_repo()
        try:
            s = Scheduler(root)
            task = s.create_task("Change payment boundary", "HIGH")
            s.ready(task["id"])
            runner = LifecycleRunner(root, self.executor("worktree"))
            result = runner.run_next("worker-1")
            self.assertEqual(result["status"], "repairing")
            self.assertEqual(result["stage"], "proof")
            self.assertEqual(s.get(task["id"])["state"], "REPAIRING")
        finally:
            td.cleanup()


if __name__ == "__main__": unittest.main()
