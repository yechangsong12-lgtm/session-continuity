"""Exercise a handoff between different workspace mounts without a live model."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent


class PortableHandoffTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "first mount"
        self.root.mkdir()
        (self.root / "quotes.csv").write_text("item,price\nA,12\n", encoding="utf-8")

    def cli(self, tool, *args, root=None, ok=True):
        result = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(SCRIPTS / f"{tool}.py"),
             "--root", str(root or self.root), "--target", "quotes", *args],
            capture_output=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode == 0, ok, result.stderr)
        return result

    def save(self, goal, host):
        self.cli("checkpoint", "--active-goal", goal, "--latest-user-request", goal,
                 "--source", host, "--decision", "A = 12", "--evidence", "quotes.csv, row 2",
                 "--open-task", "Confirm currency")

    def test_resume_from_another_mount_or_chat(self):
        self.save("Review quotes", "workbuddy")
        receiver = self.root.parent / "second mount"
        shutil.copytree(self.root, receiver)
        self.assertTrue(json.loads(self.cli("validate", root=receiver).stdout)["ok"])
        output = self.cli("bootstrap", "--portable", root=receiver).stdout
        for field in ("Revision: 1", "workbuddy", "A = 12", "quotes.csv, row 2",
                      "Confirm currency", "--target quotes", "performed at the source"):
            self.assertIn(field, output)
        for path in (self.root, receiver, SCRIPTS):
            self.assertNotIn(str(path), output)
        self.assertFalse((receiver / ".agent/continuity/targets/quotes/rollover-request.json").exists())

    def test_chinese_export_and_incomplete_package(self):
        self.save("核对报价与币种", "deepseek-harness")
        out = self.root / "接手提示.md"
        self.cli("bootstrap", "--portable", "--output", str(out))
        text = out.read_text(encoding="utf-8")
        for field in ("在接收端接手", "核对报价与币种", "deepseek-harness", "quotes.csv"):
            self.assertIn(field, text)
        manifest = self.root / ".agent/continuity/targets/quotes/manifest.json"
        valid = json.loads(manifest.read_text(encoding="utf-8"))
        del valid["files"]["handoff.md"]
        manifest.write_text(json.dumps(valid), encoding="utf-8")
        rejected = self.cli("bootstrap", "--portable", ok=False)
        self.assertFalse(rejected.stdout)
        self.assertIn("manifest", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
