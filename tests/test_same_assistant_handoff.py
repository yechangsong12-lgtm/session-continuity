"""Check the files a successor reads in a new chat in the same workspace."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "session-continuity" / "scripts"


class SameAssistantHandoffTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.workspace = Path(tmp.name)
        self.checkpoint = self.workspace / ".agent" / "continuity" / "targets" / "quotes"
        (self.workspace / "quotes.csv").write_text("item,price\nA,12\n", encoding="utf-8")

    def cli(self, tool, *args, ok=True):
        result = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(SCRIPTS / f"{tool}.py"),
             "--root", str(self.workspace), "--target", "quotes", *args],
            capture_output=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode == 0, ok, result.stderr)
        return result

    def save(self, goal):
        self.cli("checkpoint", "--active-goal", goal, "--source", "workbuddy",
                 "--decision", "A = 12", "--evidence", "quotes.csv, row 2",
                 "--context-file", "quotes.csv", "--open-task", "Confirm currency")

    def test_same_workspace_handoff_is_readable_without_a_new_chat_request(self):
        self.save("Review the quote")
        self.assertTrue(json.loads(self.cli("validate").stdout)["ok"])
        summary = (self.checkpoint / "handoff.md").read_text(encoding="utf-8")
        for item in ("Revision: 1", "workbuddy", "quotes.csv, row 2", "Confirm currency"):
            self.assertIn(item, summary)
        self.assertIn("A,12", (self.workspace / "quotes.csv").read_text(encoding="utf-8"))
        self.assertIn("Revision: 1", self.cli("bootstrap").stdout)
        self.assertFalse((self.checkpoint / "rollover-request.json").exists())

    def test_incomplete_manifest_blocks_resumption(self):
        self.save("核对报价")
        self.assertIn("修订号", (self.checkpoint / "handoff.md").read_text(encoding="utf-8"))
        manifest = self.checkpoint / "manifest.json"
        saved = json.loads(manifest.read_text(encoding="utf-8"))
        del saved["files"]["handoff.md"]
        manifest.write_text(json.dumps(saved), encoding="utf-8")
        failed = self.cli("bootstrap", ok=False)
        self.assertFalse(failed.stdout)
        self.assertIn("manifest", failed.stderr)

    def test_previous_revision_evidence_is_carried_without_renewing_approval(self):
        self.save("Check quotes")
        state_file = self.checkpoint / "current.yml"
        manifest_file = self.checkpoint / "manifest.json"
        state = json.loads(state_file.read_text(encoding="utf-8"))
        # Model historical checkpoint data that carried an optional review directory.
        state["triparty"] = {"run_dir": "old-review"}
        state["gates"]["review_status"] = "passed"
        state_file.write_text(json.dumps(state), encoding="utf-8")
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        saved = state_file.read_bytes()
        manifest["files"]["current.yml"] = {"sha256": hashlib.sha256(saved).hexdigest(), "bytes": len(saved)}
        manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
        self.assertTrue(json.loads(self.cli("validate").stdout)["ok"])

        self.cli("checkpoint", "--open-task", "Review the new quote")
        self.assertTrue(json.loads(self.cli("validate").stdout)["ok"])
        updated = json.loads(state_file.read_text(encoding="utf-8"))
        self.assertEqual(updated["revision"], 2)
        self.assertEqual(updated["gates"]["review_status"], "partial")
        self.assertIn("old-review", updated["context_to_load"])
        self.assertIn("quotes.csv", updated["context_to_load"])
        self.assertNotIn("triparty", updated)
        self.assertEqual(len(list((self.checkpoint / "snapshots").iterdir())), 2)


if __name__ == "__main__":
    unittest.main()
