import io
import json
import unittest

from dsh_context import read_snapshot


class DeepSeekSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.header = {"type": "session", "version": 4, "id": "example", "isSeeded": False,
                       "delegationDepth": 0, "createdAt": 1}
        self.events = []

    def event(self, kind, data, **extra):
        self.events.append({"seq": len(self.events), "time": 1, "type": kind, "data": data, **extra})

    def use(self, provider="sample", model="regular", window=10000):
        config = {"provider": provider, "model": model}
        self.event("request/header", {"header": {"config": config}, "reason": "initial"})
        self.event("request/context", {**config, "contextWindow": window})

    def reply(self, **usage):
        self.event("assistant/message", {"turn": 1, "step": 1, "usage": usage, "stream": []}, surfaceOp="append")

    def result(self, session="example"):
        return read_snapshot(io.StringIO("\n".join(map(json.dumps, [self.header, *self.events]))), session)

    def test_only_latest_settled_prompt_and_disjoint_cache_buckets_count(self):
        self.use()
        self.reply(inputTokens=7999, outputTokens=1000, totalTokens=8999)
        self.assertFalse(self.result()["at_or_above_80"])
        self.reply(inputTokens=10, cacheReadTokens=7980, cacheWriteTokens=10, outputTokens=300)
        value = self.result()
        self.assertTrue(value["at_or_above_80"])
        self.assertEqual((value["provider"], value["model"], value["sample_seq"], value["input_tokens"]),
                         ("sample", "regular", 3, 8000))
        self.reply(inputTokens=15, totalTokens=50000000)
        self.assertFalse(self.result()["at_or_above_80"])

    def test_changed_model_or_window_and_pending_selection(self):
        self.use()
        self.reply(inputTokens=9000)
        self.event("model/selection", {"provider": "sample", "model": "other"})
        self.assertIsNone(self.result()["model"])
        self.event("request/header", {"header": {"config": {"provider": "sample", "model": "regular"}}})
        self.assertIsNone(self.result()["at_or_above_80"])
        self.use(model="other", window=100000)
        self.assertIsNone(self.result()["at_or_above_80"])
        self.reply(inputTokens=9000)
        self.assertFalse(self.result()["at_or_above_80"])

    def test_compaction_replace_retry_and_unsettled_step(self):
        self.use()
        for kind, fields in [("compaction/end", {}), ("system/message", {"surfaceOp": {"op": "replace"}}),
                             ("llm/retry-started", {}), ("step/start", {})]:
            self.reply(inputTokens=9000)
            self.event(kind, {}, **fields)
            self.assertIsNone(self.result()["at_or_above_80"])
        self.reply(inputTokens=True)
        self.assertIsNone(self.result()["at_or_above_80"])

    def test_embedded_usage_chunk_fallback(self):
        self.use()
        self.event("assistant/message", {"stream": [{"type": "chunk", "chunk": {
            "type": "usage", "usage": {"inputTokens": 8000, "outputTokens": 120}}}]})
        self.assertTrue(self.result()["at_or_above_80"])

    def test_inherited_prefix_and_identity(self):
        self.header["isSeeded"] = True
        self.use()
        self.reply(inputTokens=8200)
        self.assertIsNone(self.result()["at_or_above_80"])
        self.event("session/end-seed", {"inherited": True})
        self.assertIsNone(self.result()["at_or_above_80"])
        self.use(model="child-own-route")
        self.reply(inputTokens=250)
        self.assertFalse(self.result()["at_or_above_80"])
        with self.assertRaises(ValueError):
            self.result("different")
        self.header["delegationDepth"] = 1
        with self.assertRaises(ValueError):
            self.result()

    def test_bad_version_and_discontinuous_snapshot(self):
        self.header["version"] = 3
        with self.assertRaises(ValueError):
            self.result()
        self.header["version"] = 4
        self.use()
        self.events[-1]["seq"] = 4
        with self.assertRaises(ValueError):
            self.result()


if __name__ == "__main__":
    unittest.main()
