"""Test destination identity, retries, and writer exclusion at the receipt CLI."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


SCRIPTS = Path(__file__).resolve().parent


class ThreadReceiptTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.state = self.root / ".agent" / "continuity"
        self.receipt = self.state / "thread-receipt.json"
        self.assert_ok("checkpoint", "--active-goal", "Verify receipt retries")
        self.prepare()

    def call(self, name, *args):
        return subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(SCRIPTS / (name + ".py")),
             "--root", str(self.root), *args],
            capture_output=True, text=True, encoding="utf-8",
        )

    def assert_ok(self, name, *args):
        result = self.call(name, *args)
        self.assertEqual(result.returncode, 0, result.stderr)

    def prepare(self):
        self.assert_ok("bootstrap", "--prepare-thread", "--thread-id", "source-A",
                       "--approved-model", "test-model")

    def test_wrong_source_and_self_destination(self):
        for args in (("--source-thread-id", "source-B", "--created-thread-id", "dest-A"),
                     ("--created-thread-id", "source-A")):
            self.assertNotEqual(self.call("thread_receipt", *args).returncode, 0)
            self.assertFalse(self.receipt.exists())

    def test_pending_promotes_once_then_retries_keep_metadata(self):
        self.assert_ok("thread_receipt", "--pending-worktree-id", "ticket-A",
                       "--target-type", "worktree", "--note", "Queued workspace")
        self.assertNotEqual(self.call("thread_receipt", "--pending-worktree-id", "ticket-B").returncode, 0)
        self.assert_ok("thread_receipt", "--created-thread-id", "dest-A")
        final_bytes = self.receipt.read_bytes()
        saved = json.loads(final_bytes)
        self.assertEqual((saved["source_thread_id"], saved["pending_worktree_id"],
                          saved["created_thread_id"], saved["status"]),
                         ("source-A", "ticket-A", "dest-A", "created"))
        self.assertEqual(saved["target_type"], "worktree")
        self.assertEqual(saved["notes"], "Queued workspace")
        self.assert_ok("thread_receipt", "--created-thread-id", "dest-A")
        for args in ((), ("--pending-worktree-id", "ticket-A"), ("--created-thread-id", "dest-B")):
            self.assertNotEqual(self.call("thread_receipt", *args).returncode, 0)
        self.assertEqual(self.receipt.read_bytes(), final_bytes)

    def test_new_revision_can_record_new_destination(self):
        self.assert_ok("thread_receipt", "--created-thread-id", "first")
        self.assert_ok("checkpoint", "--active-goal", "Second transfer")
        self.prepare()
        self.assert_ok("thread_receipt", "--created-thread-id", "second")
        saved = json.loads(self.receipt.read_bytes())
        self.assertEqual(saved["created_thread_id"], "second")
        self.assertEqual(saved["continuity_revision"], 2)

    def test_model_cannot_be_rebound_after_pending_or_creation(self):
        path = self.state / "rollover-request.json"
        original_request = path.read_bytes()
        self.assert_ok("thread_receipt", "--pending-worktree-id", "ticket-A")
        for args in (("--pending-worktree-id", "ticket-A"), ("--created-thread-id", "dest-A")):
            self.assert_ok("thread_receipt", *args)
            original_receipt = self.receipt.read_bytes()
            self.prepare()
            other = self.call("bootstrap", "--prepare-thread", "--thread-id", "source-A",
                              "--approved-model", "different-model")
            self.assertNotEqual(other.returncode, 0)
            self.assertEqual(path.read_bytes(), original_request)
            self.assert_ok("thread_receipt", *args)
            self.assertEqual(self.receipt.read_bytes(), original_receipt)

    def test_retry_keeps_receipt_when_older_software_replaced_request(self):
        self.assert_ok("thread_receipt", "--pending-worktree-id", "ticket-A")
        path = self.state / "rollover-request.json"
        original_request = path.read_bytes()
        replacement = json.loads(original_request)
        replacement["approved_model"] = "different-model"
        original_pending = self.receipt.read_bytes()
        path.write_text(json.dumps(replacement), encoding="utf-8")
        self.assertNotEqual(self.call("thread_receipt", "--created-thread-id", "dest-A").returncode, 0)
        self.assertEqual(self.receipt.read_bytes(), original_pending)
        path.write_bytes(original_request)
        self.assert_ok("thread_receipt", "--created-thread-id", "dest-A")
        original_receipt = self.receipt.read_bytes()
        path.write_text(json.dumps(replacement), encoding="utf-8")
        self.assert_ok("thread_receipt", "--created-thread-id", "dest-A")
        self.assertEqual(self.receipt.read_bytes(), original_receipt)

    def test_competing_destinations_have_one_winner(self):
        destinations = ["dest-A", "dest-B", "dest-C", "dest-D"]
        with ThreadPoolExecutor(len(destinations)) as pool:
            results = list(pool.map(lambda dest: self.call("thread_receipt", "--created-thread-id", dest),
                                    destinations))
        winners = [dest for dest, result in zip(destinations, results) if result.returncode == 0]
        self.assertEqual(winners, [json.loads(self.receipt.read_bytes())["created_thread_id"]])

    def test_fresh_incomplete_writer_lock_is_preserved(self):
        lock = self.state / "locks" / "writer.lock"
        lock.touch()
        result = self.call("thread_receipt", "--created-thread-id", "dest-A")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(lock.exists())
        self.assertFalse(self.receipt.exists())

    def test_live_owner_keeps_aged_writer_lock(self):
        lock = self.state / "locks" / "writer.lock"
        original = json.dumps({"pid": os.getpid()}).encode()
        lock.write_bytes(original)
        expired = time.time() - 901
        os.utime(lock, (expired, expired))
        result = self.call("thread_receipt", "--created-thread-id", "dest-A")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(lock.read_bytes(), original)
        self.assertFalse(self.receipt.exists())


if __name__ == "__main__":
    unittest.main()
