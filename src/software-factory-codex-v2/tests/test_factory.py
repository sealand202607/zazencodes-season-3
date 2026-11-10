"""Exercise the installed template with real Git worktrees and an in-memory GitHub."""
import contextlib
import io
import json
import runpy
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TEMPLATE = Path(__file__).resolve().parents[1]


class FactoryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "target repo"
        self.root.mkdir()
        self.remote = Path(temp.name) / "origin.git"
        self.run_cmd("git", "init", "-qb", "main")
        self.run_cmd("git", "config", "user.name", "Factory Test")
        self.run_cmd("git", "config", "user.email", "factory@example.invalid")
        self.run_cmd("git", "init", "-q", "--bare", self.remote)
        self.run_cmd("git", "remote", "add", "origin", self.remote)
        self.run_cmd(TEMPLATE / "install.sh", self.root)
        self.factory = self.root / "factory"
        self.job = runpy.run_path(str(self.factory / "bin/job"))
        self.pr_state = "OPEN"
        self.is_draft = True
        self.labels = ["factory"]
        mock = patch.dict(self.job["main"].__globals__, gh=self.gh)
        mock.start()
        self.addCleanup(mock.stop)

    def run_cmd(self, *args, cwd=None, check=True):
        return subprocess.run(args, cwd=cwd or self.root, check=check, text=True,
                              capture_output=True)

    def gh(self, *args):
        command = args[:2]
        if command == ("api", "user"):
            return "operator"
        if command == ("issue", "view"):
            return json.dumps(dict(number=1, title="Add subtraction", body="Support subtraction.",
                                   author={"login": "author"}, labels=[{"name": x} for x in self.labels],
                                   state="OPEN", url="https://example.invalid/issues/1", comments=[]))
        if command == ("issue", "comment"):
            return ""
        if command == ("pr", "list"):
            return json.dumps([{"number": 2, "url": "https://example.invalid/pull/2"}])
        if command == ("pr", "view"):
            return json.dumps({"state": self.pr_state, "isDraft": self.is_draft})
        if command == ("pr", "ready"):
            self.is_draft = False
            return ""
        if command == ("pr", "merge"):
            self.assertFalse(self.is_draft)
            self.run_cmd("git", "update-ref", "refs/heads/main", self.branch, cwd=self.remote)
            self.pr_state = "MERGED"
            return ""
        self.fail(f"unexpected GitHub call {args!r}")

    def job_cmd(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.job["main"](list(args))
        return out.getvalue().strip()

    def test_install(self):
        self.assertEqual(len(list((self.root / ".codex/agents").glob("*.toml"))), 8)
        self.assertTrue((self.root / ".agents/skills/factory/SKILL.md").is_file())
        self.assertEqual(self.run_cmd("git", "check-ignore", "factory/jobs/x", ".worktrees/x")
                         .stdout.splitlines(), ["factory/jobs/x", ".worktrees/x"])
        self.assertNotEqual(self.run_cmd("bash", "factory/checks.sh", check=False).returncode, 0)
        checks = self.factory / "checks.sh"
        checks.write_text("existing project checks\n")
        self.assertNotEqual(self.run_cmd(TEMPLATE / "install.sh", self.root, check=False).returncode, 0)
        self.assertEqual(checks.read_text(), "existing project checks\n")

    def test_queue_label_required(self):
        self.labels = []
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.job_cmd("create", "1")
        self.assertFalse((self.factory / "jobs").exists())

    def test_failed_gate_retry_review_and_merge(self):
        (self.factory / "checks.sh").write_text('test "$(cat feature)" = ready\n')
        self.run_cmd("git", "add", ".")
        self.run_cmd("git", "commit", "-qm", "Initial project")
        self.run_cmd("git", "push", "-qu", "origin", "main")
        job_id = self.job_cmd("create", "1")
        folder = self.factory / "jobs" / job_id
        (folder / "intake.md").write_text("DECISION: ACCEPT\nRISK: high\nSURFACES: ui, security\n")
        self.run_cmd(self.factory / "bin/route", job_id)
        state = json.loads((folder / "job.json").read_text())
        self.assertEqual(state["agents"]["reviewers"],
                         dict(code=None, ui=None, ux=None, security=None))
        self.branch = state["branch"]
        tree = Path(state["worktree"])
        def advance(stage):
            self.job_cmd("advance", job_id, stage)

        advance("spec")
        (folder / "spec.md").write_text("Implement the feature.\n")
        advance("build")
        for round_number, value in [(1, "broken"), (2, "ready")]:
            (tree / "feature").write_text(value + "\n")
            self.run_cmd("git", "add", "feature", cwd=tree)
            self.run_cmd("git", "commit", "-qm", f"Round {round_number}", cwd=tree)
            self.run_cmd("git", "push", "-qu", "origin", self.branch, cwd=tree)
            (folder / "build.md").write_text("STATUS: READY\n")
            advance("gate")
            gate = self.run_cmd(self.factory / "bin/gate", job_id, check=False)
            if round_number == 1:
                self.assertEqual(gate.returncode, 1)
                with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                    advance("review")
                advance("build")
            else:
                self.assertEqual(gate.returncode, 0)
                advance("review")
        for r in ["code", "ux", "ui"]:
            (folder / f"round-2/review-{r}.md").write_text("VERDICT: PASS\n")
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            advance("approve")
        (folder / "round-2/review-security.md").write_text("VERDICT: PASS\n")
        advance("approve")
        (folder / "decision.md").write_text("APPROVE\n")
        self.job_cmd("merge", job_id)
        self.assertEqual(json.loads((folder / "job.json").read_text())["stage"], "merged")
        self.assertTrue((folder / "round-2/merge-checks.md").read_text().startswith("GATE: PASS\n"))
        self.assertEqual(self.run_cmd("git", "show", "main:feature", cwd=self.remote).stdout, "ready\n")
        self.assertFalse(tree.exists())
        self.assertIn("merged", self.job_cmd("summary", job_id))


if __name__ == "__main__":
    unittest.main()
