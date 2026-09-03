import unittest
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]
CHECKOUT_V7 = "3d3c42e5aac5ba805825da76410c181273ba90b1"
SETUP_PYTHON_V7 = "5fda3b95a4ea91299a34e894583c3862153e4b97"


class ReleasePresentationV3Tests(unittest.TestCase):
    def test_readme_is_flagship_and_uses_real_cli_surfaces(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for heading in (
            "# Architecture",
            "# How a change moves through Foundry",
            "# Quick start",
            "# Security and trust boundaries",
            "# Evidence before trust",
            "# Validation status",
        ):
            self.assertIn(heading, text)
        self.assertIn("nakeuri lifecycle-run", text)
        self.assertNotIn('nakeuri run "', text)
        version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
        self.assertIn(version, text)
        self.assertTrue((ROOT / "docs" / "V5_FLAGSHIP_PROOF.md").exists())
        self.assertTrue((ROOT / "docs" / "V5_EMPIRICAL_BENCHMARK.md").exists())

    def test_github_release_docs_are_current(self):
        github_ready = (ROOT / "GITHUB_READY.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
        self.assertIn("v5.0.0-alpha.1", github_ready)
        self.assertIn("5.0.0a1", github_ready)
        self.assertNotIn("2.0.0b1", github_ready)
        self.assertNotIn("2.0.0b1", roadmap)
        self.assertTrue((ROOT / "docs" / "GITHUB_RELEASE.md").exists())
        mcp_server = (ROOT / "src" / "flutter_foundry" / "mcp_server.py").read_text(encoding="utf-8")
        self.assertIn("version=__version__", mcp_server)
        self.assertIn("UnifiedLifecycleExecutor.default", mcp_server)
        self.assertNotIn("version='4.0.0a1'", mcp_server)

    def test_dependabot_covers_actions_and_python(self):
        text = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
        self.assertIn('package-ecosystem: "github-actions"', text)
        self.assertIn('package-ecosystem: "pip"', text)
        self.assertGreaterEqual(text.count('interval: "weekly"'), 2)

    def test_repository_workflows_use_current_pinned_action_generations(self):
        text = "\n".join(
            p.read_text(encoding="utf-8")
            for p in sorted((ROOT / ".github" / "workflows").glob("*.yml"))
        )
        self.assertIn(f"actions/checkout@{CHECKOUT_V7}", text)
        self.assertIn(f"actions/setup-python@{SETUP_PYTHON_V7}", text)
        self.assertNotIn("actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683", text)
        self.assertNotIn("actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", text)

    def test_generated_workflows_enforce_machine_exit_codes(self):
        pr_gate = (ROOT / "templates" / "github" / "flutter-pr-ci.yml").read_text(encoding="utf-8")
        release_gate = (ROOT / "templates" / "github" / "release-gate.yml").read_text(encoding="utf-8")
        self.assertIn("flutter-foundry --ci --compact gate .", pr_gate)
        self.assertIn("flutter-foundry --ci --compact production-check .", release_gate)
        self.assertIn("flutter-foundry --ci --allow-gaps --compact verify . --profile release", release_gate)
        self.assertNotIn("flutter build appbundle --release", release_gate)

    def test_benchmark_methodology_preserves_claim_boundary(self):
        text = (ROOT / "docs" / "BENCHMARK_METHODOLOGY.md").read_text(encoding="utf-8")
        for phrase in (
            "Fair comparison contract",
            "Official Flutter AI stack",
            "VGV Wingspan",
            "OpenHands",
            "OpenAI Symphony",
            "hidden acceptance tests",
            "better than OpenHands",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
