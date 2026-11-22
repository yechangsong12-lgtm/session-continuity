"""Exercise the registered Codex command protocol in an isolated user directory."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from uuid import uuid4


SCRIPT = Path(__file__).with_name("context-reminder.py")


class ContextHookTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        self.thread = str(uuid4())
        self.log = self.home / "sessions" / f"rollout-test-{self.thread}.jsonl"
        self.log.parent.mkdir()
        self.settings = self.home / "hooks" / "session-continuity.json"
        self.settings.parent.mkdir()
        self.record("session_meta", {"source": "cli"})

    def record(self, kind, payload):
        with self.log.open("a", encoding="utf-8") as stream:
            print(json.dumps({"type": kind, "payload": payload}), file=stream)

    def sample(self, count):
        self.record("event_msg", {"type": "token_count", "info": {
            "last_token_usage": {"total_tokens": count}, "model_context_window": 10000,
            "total_token_usage": {"total_tokens": 900000},
        }})

    def enable(self):
        self.settings.write_text('{"auto_handoff_at_80": true}', encoding="utf-8")

    def fire(self, event, **fields):
        payload = {"session_id": self.thread, "transcript_path": str(self.log),
                   "hook_event_name": event, **fields}
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT)], env={**os.environ, "CODEX_HOME": str(self.home)},
            input=json.dumps(payload), capture_output=True, text=True, timeout=10, check=True,
        )
        return json.loads(result.stdout) if result.stdout else None

    def test_threshold_and_mode_upgrade(self):
        self.sample(7999)
        self.assertIsNone(self.fire("UserPromptSubmit"))
        self.sample(8000)
        self.assertEqual(set(self.fire("Stop")), {"systemMessage"})
        self.assertIsNone(self.fire("Stop"))
        self.enable()
        result = self.fire("UserPromptSubmit")
        self.assertEqual(result["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        self.assertIn("$session-continuity", result["hookSpecificOutput"]["additionalContext"])
        self.assertIsNone(self.fire("Stop"))
        self.sample(100)
        self.assertIsNone(self.fire("UserPromptSubmit"))
        self.sample(8500)
        self.assertEqual(self.fire("Stop")["decision"], "block")
        self.assertIsNone(self.fire("Stop", stop_hook_active=True))

    def test_deferred_after_compaction(self):
        for event, extra in (("SessionStart", {"source": "compact"}), ("PostToolUse", {})):
            self.enable()
            self.sample(8000)
            self.assertIsNone(self.fire("PreCompact", trigger="auto"))
            self.record("compacted", {})
            result = self.fire(event, **extra)
            self.assertEqual(result["hookSpecificOutput"]["hookEventName"], event)
            self.assertIsNone(self.fire("PostToolUse"))

    def test_competing_events_deliver_once(self):
        self.enable()
        self.sample(8200)
        with ThreadPoolExecutor(4) as executor:
            events = ["PostToolUse", "UserPromptSubmit", "Stop", "PostToolUse"]
            results = list(executor.map(self.fire, events))
        self.assertEqual(sum(r is not None for r in results), 1)

    def test_child_and_invalid_settings(self):
        self.enable()
        self.sample(8200)
        self.assertIsNone(self.fire("PostToolUse", subagent={"id": "child"}))
        self.settings.write_text('{"auto_handoff_at_80": "true"}', encoding="utf-8")
        self.assertEqual(set(self.fire("Stop")), {"systemMessage"})
        self.enable()
        self.log.write_text("", encoding="utf-8")
        self.record("session_meta", {"source": {"subagent": {"thread_spawn": {}}}})
        self.sample(9000)
        self.assertIsNone(self.fire("PostToolUse"))


if __name__ == "__main__":
    unittest.main()
