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

    @property
    def pending(self):
        return self.settings.parent / "context-reminder-state" / (self.thread + ".pending")

    def fire(self, event, ui_locale=None, **fields):
        payload = {"session_id": self.thread, "transcript_path": str(self.log),
                   "hook_event_name": event, **fields}
        env = {**os.environ, "CODEX_HOME": str(self.home)}
        if ui_locale:
            env["LC_ALL"] = ui_locale
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT)], env=env,
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

    def test_compaction_discards_old_high_sample(self):
        for event, extra in (("SessionStart", {"source": "compact"}), ("PostToolUse", {})):
            self.enable()
            self.sample(8000)
            self.assertIsNone(self.fire("PreCompact", trigger="auto"))
            snapshot = json.loads(self.pending.read_text(encoding="ascii"))
            self.assertEqual(snapshot["session_id"], self.thread)
            self.assertEqual((snapshot["used"], snapshot["window"]), (8000, 10000))
            with self.log.open("rb") as stream:
                stream.seek(snapshot["offset"])
                source = json.loads(stream.readline())["payload"]["info"]
            self.assertEqual(source["last_token_usage"]["total_tokens"], snapshot["used"])
            self.record("compacted", {})
            self.sample(125)
            self.assertIsNone(self.fire(event, **extra))
            self.assertFalse(self.pending.exists())
            self.assertIsNone(self.fire("PostToolUse"))

    def test_historical_marker_never_overrides_current_sample(self):
        self.enable()
        self.sample(8000)
        self.fire("PreCompact")
        self.record("compacted", {})
        original = json.loads(self.pending.read_text(encoding="ascii"))
        for alteration in ({"session_id": str(uuid4())}, {"used": 9999}, {"offset": 1},
                           {"observed_utc": "arbitrary injected instructions"}):
            self.pending.write_text(json.dumps({**original, **alteration}), encoding="ascii")
            self.assertIsNone(self.fire("PostToolUse"))
        self.pending.write_text(json.dumps(original), encoding="ascii")
        self.log.write_text(self.log.read_text(encoding="utf-8").replace("8000", "7000"), encoding="utf-8")
        self.assertIsNone(self.fire("PostToolUse"))
        self.pending.touch()
        self.assertIsNone(self.fire("PostToolUse"))

    def test_empty_legacy_pending_is_quiet_after_reset(self):
        self.enable()
        self.sample(8350)
        self.record("compacted", {})
        self.pending.parent.mkdir()
        self.pending.touch()
        self.assertIsNone(self.fire("Stop"))
        self.assertFalse(self.pending.exists())
        self.assertIsNone(self.fire("Stop"))

    def test_current_high_checkpoint_preserves_permission_and_model_choice(self):
        self.settings.write_text('{"auto_checkpoint_at_80": true}', encoding="ascii")
        self.sample(8050)
        self.fire("PreCompact")
        old_snapshot = json.loads(self.pending.read_text(encoding="ascii"))
        self.sample(8250)
        result = self.fire("UserPromptSubmit", prompt="继续")
        delivered = json.loads(self.pending.with_suffix(".handoff").read_text(encoding="ascii"))
        self.assertEqual(delivered["used"], 8250)
        self.assertGreater(delivered["offset"], old_snapshot["offset"])
        context = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("8250/10000", context)
        self.assertIn(f"byte offset {delivered['offset']} ", context)
        self.assertIn(delivered["observed_utc"], context)
        self.assertIn("save and validate a checkpoint in this chat", context)
        self.assertIn("which model", context)
        self.assertIn("'continue' or '继续'", context)
        self.assertNotIn("ask whether to archive the source", context)
        self.assertIsNone(self.fire("PostToolUse"))

    def test_simulated_marker_is_ignored_without_a_current_high_sample(self):
        self.enable()
        self.pending.parent.mkdir()
        simulated = {"session_id": self.thread, "used": 8000, "window": 10000,
                     "offset": 12, "simulated": True}
        self.pending.write_text(json.dumps(simulated), encoding="ascii")
        self.assertIsNone(self.fire("UserPromptSubmit", prompt="继续"))
        self.sample(7999)
        self.pending.write_text(json.dumps(simulated), encoding="ascii")
        self.assertIsNone(self.fire("Stop"))
        self.assertFalse(self.pending.exists())

    def test_new_checkpoint_preference_overrides_legacy_name(self):
        self.settings.write_text('{"auto_checkpoint_at_80": false,"auto_handoff_at_80": true}', encoding="ascii")
        self.sample(8000)
        self.assertEqual(set(self.fire("PostToolUse")), {"systemMessage"})

    def test_localized_ui_preserves_conversation_language_instruction(self):
        self.enable()
        for ui_locale, expected in (("zh_CN.UTF-8", "主对话"), ("en_US.UTF-8", "This chat")):
            self.sample(8000)
            response = self.fire("Stop", ui_locale=ui_locale)
            self.assertIn(expected, response["systemMessage"])
            self.assertIn("language requested by the user", response["reason"])
            self.sample(1000)
            self.assertIsNone(self.fire("Stop"))

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
