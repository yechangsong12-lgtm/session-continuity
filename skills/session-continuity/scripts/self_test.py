#!/usr/bin/env python3
"""Run a local smoke test for the session-continuity skill."""

from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4


SCRIPT_DIR = Path(__file__).resolve().parent


def run(args: list[str], *, input_text: str | None = None, expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        [sys.executable, *args],
        text=True,
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if expect_ok and proc.returncode != 0:
        raise AssertionError(f"command failed: {args}\nstdout={proc.stdout}\nstderr={proc.stderr}")
    if not expect_ok and proc.returncode == 0:
        raise AssertionError(f"command unexpectedly succeeded: {args}\nstdout={proc.stdout}")
    return proc


def test_confirmed_source_model(root: Path) -> None:
    fake_home = root / "isolated-codex"
    sessions = fake_home / "sessions" / "2026" / "11"
    sessions.mkdir(parents=True)
    source = str(uuid4())
    other = str(uuid4())
    workspace = root / "model-work"
    workspace.mkdir()

    def append(chat: str, kind: str, payload: dict) -> None:
        with (sessions / f"rollout-test-{chat}.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"type": kind, "payload": payload}) + "\n")

    def measure(chat: str, used: int) -> None:
        append(chat, "event_msg", {"type": "token_count", "info": {
            "last_token_usage": {"total_tokens": used}, "model_context_window": 10000,
            "total_token_usage": {"total_tokens": 9999999},
        }})

    def inspect(*options: str, expect_ok: bool = True):
        return run([str(SCRIPT_DIR / "bootstrap.py"), "--root", str(workspace), *options], expect_ok=expect_ok)

    with patch.dict(os.environ, {"CODEX_HOME": str(fake_home), "CODEX_THREAD_ID": source}):
        append(source, "session_meta", {"id": source})
        append(source, "turn_context", {"model": "first-model"})
        measure(source, 7999)
        append(other, "session_meta", {"id": other})
        append(other, "turn_context", {"model": "unrelated-model"})
        measure(other, 9999)
        preview = json.loads(inspect("--show-source-model", "--thread-id", source).stdout)
        assert preview["source_model"] == "first-model" and preview["at_or_above_80"] is False
        assert not (workspace / ".agent").exists()

        run([str(SCRIPT_DIR / "checkpoint.py"), "--root", str(workspace), "--latest-user-request", "Check a source model"])
        request = workspace / ".agent" / "continuity" / "rollover-request.json"
        prepare = ["--prepare-thread", "--inherit-source-model", "--thread-id", source]
        inspect(*prepare, expect_ok=False)
        assert not request.exists()
        measure(source, 8000)
        inspect(*prepare, "--expected-source-model", preview["source_model"])
        data = json.loads(request.read_text(encoding="utf-8"))
        assert data["approved_model"] == "first-model" and data["metrics"]["used_tokens"] == 8000
        request.unlink()

        append(source, "turn_context", {"model": "switched-model"})
        assert json.loads(inspect("--show-source-model").stdout)["source_model"] == "switched-model"
        inspect(*prepare, expect_ok=False)  # Do not recycle the previous model's high sample.
        assert not request.exists()
        measure(source, 8400)
        for override in ([], ["--approved-model", "user-pick"]):
            rejected = inspect(*prepare, "--expected-source-model", preview["source_model"], *override, expect_ok=False)
            assert json.loads(rejected.stderr)["source_model"] == "switched-model" and not request.exists()
        inspect(*prepare, "--expected-source-model", "switched-model")
        assert json.loads(request.read_text(encoding="utf-8"))["approved_model"] == "switched-model"
        inspect(*prepare, "--approved-model", "user-pick")
        data = json.loads(request.read_text(encoding="utf-8"))
        assert data["approved_model"] == "user-pick" and data["trigger"]["model_selection"] == "user_override"
        request.unlink()
        append(source, "compacted", {"message": "test"})
        inspect(*prepare, "--approved-model", "user-pick", expect_ok=False)
        measure(source, 1200)
        inspect(*prepare, expect_ok=False)
        append(source, "turn_context", {})
        measure(source, 9999)
        inspect("--show-source-model", expect_ok=False)
        inspect(*prepare, expect_ok=False)

        missing = str(uuid4())
        inspect("--show-source-model", "--thread-id", missing, expect_ok=False)
        append(missing, "session_meta", {"id": other})
        append(missing, "turn_context", {"model": "wrong-owner"})
        inspect("--show-source-model", "--thread-id", missing, expect_ok=False)
        assert not request.exists()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="session-continuity $-O'Brien-") as tmp:
        root = Path(tmp)
        test_confirmed_source_model(root)
        checkpoint = run(
            [
                str(SCRIPT_DIR / "checkpoint.py"),
                "--root",
                str(root),
                "--workstream",
                "self-test",
                "--latest-user-request",
                "avoid manual summaries",
                "--active-goal",
                "verify continuity scripts",
                "--decision",
                "File-backed state is source of truth",
                "--open-task",
                "resume from bootstrap",
            ]
        )
        checkpoint_data = json.loads(checkpoint.stdout)
        assert checkpoint_data["ok"] is True
        validate = run([str(SCRIPT_DIR / "validate.py"), "--root", str(root)])
        validate_data = json.loads(validate.stdout)
        assert validate_data["ok"] is True
        bootstrap = run([str(SCRIPT_DIR / "bootstrap.py"), "--root", str(root)])
        assert "Resume This Workstream" in bootstrap.stdout
        targeted = run(
            [
                str(SCRIPT_DIR / "checkpoint.py"),
                "--root",
                str(root),
                "--target",
                "pricing-ui",
                "--workstream",
                "self-test:pricing-ui",
                "--latest-user-request",
                "Targeted handoff: pricing-ui",
                "--active-goal",
                "Summarize only pricing UI follow-up work",
                "--decision",
                "Only pricing UI context is included",
                "--evidence",
                "inputs/source.csv row 3",
                "--changed-file",
                "output/pricing.csv",
                "--open-task",
                "Continue pricing UI in a new session",
            ]
        )
        assert json.loads(targeted.stdout)["ok"] is True
        targeted_validate = run([str(SCRIPT_DIR / "validate.py"), "--root", str(root), "--target", "pricing-ui"])
        assert json.loads(targeted_validate.stdout)["ok"] is True
        targeted_bootstrap = run([str(SCRIPT_DIR / "bootstrap.py"), "--root", str(root), "--target", "pricing-ui",
                                  "--prepare-thread", "--approved-model", "test-model", "--thread-id", "test-source"])
        assert ".agent/continuity/targets/pricing-ui/current.yml" in targeted_bootstrap.stdout
        target_dir = root / ".agent" / "continuity" / "targets" / "pricing-ui"
        handoff = (target_dir / "handoff.md").read_text(encoding="utf-8")
        assert "inputs/source.csv row 3" in handoff and "output/pricing.csv" in handoff
        saved_request = json.loads((target_dir / "rollover-request.json").read_text(encoding="utf-8"))
        assert saved_request["prompt"] == targeted_bootstrap.stdout
        assert saved_request["source_thread_id"] == "test-source"
        assert saved_request["validation"]["revision"] == json.loads(targeted.stdout)["revision"]
        command = targeted_bootstrap.stdout.split("```", 2)[1].splitlines()[1]
        shell = ["powershell", "-NoProfile", "-NonInteractive", "-Command"] if os.name == "nt" else ["sh", "-c"]
        resumed = subprocess.run([*shell, command], check=True, capture_output=True, text=True)
        validation = json.loads(resumed.stdout)
        assert validation["ok"] and Path(validation["continuity_dir"]) == target_dir
        received = run([str(SCRIPT_DIR / "thread_receipt.py"), "--root", str(root), "--target", "pricing-ui",
                        "--created-thread-id", "test-destination"])
        assert json.loads(received.stdout)["status"] == "created"
        low_log = root / "low-context.jsonl"
        low_log.write_text(
            json.dumps(
                {
                    "timestamp": "2026-01-01T00:00:00Z",
                    "type": "session_meta",
                    "payload": {"base_instructions": {"text": "The word compaction in instructions is not a runtime compaction event."}},
                }
            )
            + "\n"
            + json.dumps(
                {
                    "timestamp": "2026-01-01T00:00:00Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "last_token_usage": {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110},
                            "model_context_window": 1000,
                        },
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        low_guard = run([str(SCRIPT_DIR / "guard.py"), "--root", str(root / "guard-low"), "--session-log", str(low_log)])
        low_guard_data = json.loads(low_guard.stdout)
        assert low_guard_data["evaluation"]["severity"] == "ok"
        assert low_guard_data["checkpoint"] is None

        false_compaction_log = root / "false-compaction.jsonl"
        false_compaction_log.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "timestamp": "2026-01-01T00:00:00Z",
                            "type": "session_meta",
                            "payload": {"base_instructions": {"text": "context compaction is mentioned in docs"}},
                        }
                    ),
                    json.dumps(
                        {
                            "timestamp": "2026-01-01T00:00:01Z",
                            "type": "turn_context",
                            "payload": {"summary": "resume facts without any runtime compaction event"},
                        }
                    ),
                    json.dumps(
                        {
                            "timestamp": "2026-01-01T00:00:02Z",
                            "type": "response_item",
                            "payload": {
                                "type": "function_call_output",
                                "output": "ordinary tool output containing compact and compaction words",
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "timestamp": "2026-01-01T00:00:03Z",
                            "type": "event_msg",
                            "payload": {
                                "type": "token_count",
                                "info": {
                                    "last_token_usage": {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110},
                                    "model_context_window": 1000,
                                },
                            },
                        }
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        false_guard = run(
            [str(SCRIPT_DIR / "guard.py"), "--root", str(root / "guard-false-compaction"), "--session-log", str(false_compaction_log)]
        )
        false_guard_data = json.loads(false_guard.stdout)
        assert false_guard_data["metrics"]["compaction_markers"] == 0
        assert false_guard_data["evaluation"]["severity"] == "ok"

        explicit_compaction_log = root / "explicit-compaction.jsonl"
        explicit_compaction_log.write_text(
            json.dumps(
                {
                    "timestamp": "2026-01-01T00:00:00Z",
                    "type": "event_msg",
                    "payload": {"type": "context_compacted"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        explicit_guard = run(
            [str(SCRIPT_DIR / "guard.py"), "--root", str(root / "guard-explicit-compaction"), "--session-log", str(explicit_compaction_log)]
        )
        explicit_guard_data = json.loads(explicit_guard.stdout)
        assert explicit_guard_data["metrics"]["compaction_markers"] == 1
        assert explicit_guard_data["evaluation"]["action"] == "review_in_current_chat"

        high_log = root / "high-context.jsonl"
        high_log.write_text(
            json.dumps(
                {
                    "timestamp": "2026-01-01T00:00:00Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "last_token_usage": {"input_tokens": 900, "output_tokens": 20, "total_tokens": 920},
                            "model_context_window": 1000,
                        },
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        rollover_root = root / "guard-rollover"
        guard_rollover = run(
            [
                str(SCRIPT_DIR / "guard.py"),
                "--root",
                str(rollover_root),
                "--session-log",
                str(high_log),
                "--thread-id",
                "019f-source-thread",
                "--checkpoint",
                "--write-request",
                "--latest-user-request",
                "Context guard rollover",
                "--active-goal",
                "Verify automatic rollover request generation",
                "--next-task",
                "Start a fresh thread from bootstrap",
            ]
        )
        guard_rollover_data = json.loads(guard_rollover.stdout)
        assert guard_rollover_data["evaluation"]["action"] == "review_in_current_chat"
        assert guard_rollover_data["checkpoint"]["ok"] is True
        request_path = rollover_root / ".agent" / "continuity" / "rollover-request.json"
        assert request_path.exists()
        request_data = json.loads(request_path.read_text(encoding="utf-8"))
        assert request_data["status"] == "ready"
        assert request_data["source_thread_id"] == "019f-source-thread"
        assert request_data["prompt_sha256"]
        assert request_data["thread_action"] == "confirm_chat_and_model"
        premature = run([str(SCRIPT_DIR / "thread_receipt.py"), "--root", str(rollover_root),
                         "--created-thread-id", "unapproved"], expect_ok=False)
        assert "require user confirmation" in premature.stderr
        unselected = run([str(SCRIPT_DIR / "bootstrap.py"), "--root", str(rollover_root),
                          "--prepare-thread"], expect_ok=False)
        assert "model choice" in unselected.stderr
        run([str(SCRIPT_DIR / "bootstrap.py"), "--root", str(rollover_root), "--prepare-thread",
             "--approved-model", "test-model", "--thread-id", "019f-source-thread"])
        approved = json.loads(request_path.read_text(encoding="utf-8"))
        assert approved["thread_action"] == "create_thread" and approved["approved_model"] == "test-model"
        receipt = run(
            [
                str(SCRIPT_DIR / "thread_receipt.py"),
                "--root",
                str(rollover_root),
                "--created-thread-id",
                "019f-test-thread",
                "--target-type",
                "projectless",
            ]
        )
        receipt_data = json.loads(receipt.stdout)
        assert receipt_data["ok"] is True
        receipt_path = rollover_root / ".agent" / "continuity" / "thread-receipt.json"
        recorded_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert recorded_receipt["created_thread_id"] == "019f-test-thread"
        assert recorded_receipt["source_thread_id"] == "019f-source-thread"
        assert recorded_receipt["rollover_request_sha256"] == hashlib.sha256(request_path.read_bytes()).hexdigest()

        no_request_root = root / "receipt-no-request"
        run(
            [
                str(SCRIPT_DIR / "checkpoint.py"),
                "--root",
                str(no_request_root),
                "--workstream",
                "receipt-no-request",
                "--active-goal",
                "verify receipts cannot claim creation without a request",
            ]
        )
        no_request_receipt = run(
            [
                str(SCRIPT_DIR / "thread_receipt.py"),
                "--root",
                str(no_request_root),
                "--created-thread-id",
                "019f-missing-request-thread",
            ],
            expect_ok=False,
        )
        assert "missing rollover-request.json" in no_request_receipt.stderr

        run(
            [
                str(SCRIPT_DIR / "checkpoint.py"),
                "--root",
                str(rollover_root),
                "--workstream",
                "guard-rollover",
                "--active-goal",
                "advance continuity revision after request generation",
                "--decision",
                "This checkpoint intentionally makes the previous rollover request stale",
            ]
        )
        stale_receipt = run(
            [
                str(SCRIPT_DIR / "thread_receipt.py"),
                "--root",
                str(rollover_root),
                "--created-thread-id",
                "019f-stale-request-thread",
            ],
            expect_ok=False,
        )
        assert "rollover request revision does not match current continuity revision" in stale_receipt.stderr
        fake_openai_key = "sk-" + "abcdefghijklmnopqrstuvwxyz1234567890"
        fake_openai_var = "OPENAI_" + "API_KEY"
        redacted = run(
            [str(SCRIPT_DIR / "redact.py")],
            input_text=f"{fake_openai_var}={fake_openai_key}\n",
        )
        assert fake_openai_key not in redacted.stdout
        url_redacted = run(
            [str(SCRIPT_DIR / "redact.py")],
            input_text="DATABASE_URL=postgres://user:password@host/db\n",
        )
        assert "password@host" not in url_redacted.stdout
        current = root / ".agent" / "continuity" / "current.yml"
        current.write_text(current.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        tampered = run([str(SCRIPT_DIR / "validate.py"), "--root", str(root)], expect_ok=False)
        assert "hash mismatch" in tampered.stdout

        lock_root = root / "lock-check"
        run(
            [
                str(SCRIPT_DIR / "checkpoint.py"),
                "--root",
                str(lock_root),
                "--workstream",
                "lock-check",
                "--active-goal",
                "verify active lock blocks resume",
            ]
        )
        lock_path = lock_root / ".agent" / "continuity" / "locks" / "writer.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(json.dumps({"pid": os.getpid() + 999999, "created_at": "now"}), encoding="utf-8")
        lock_validate = run([str(SCRIPT_DIR / "validate.py"), "--root", str(lock_root)], expect_ok=False)
        assert "active writer lock" in lock_validate.stdout
        with subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.read()"], stdin=subprocess.PIPE) as writer:
            try:
                lock_path.write_text(json.dumps({"pid": writer.pid}), encoding="utf-8")
                locked = run([str(SCRIPT_DIR / "validate.py"), "--root", str(lock_root)], expect_ok=False)
                assert "active writer lock" in locked.stdout and writer.poll() is None
            finally:
                writer.communicate(input=b"done", timeout=10)

        tri_root = root / "tri"
        run_dir = root / "triparty-run"
        run_dir.mkdir(parents=True)
        artifacts = {
            "claude-review.md": "---\nparty: Claude\nstage: review\n---\nTRIPARTY_REVIEW_COMPLETE\n",
            "gemini-review.md": "---\nparty: Gemini\nstage: review\n---\nTRIPARTY_REVIEW_COMPLETE\n",
            "claude-cross-audit.md": "---\nparty: Claude\nstage: cross-audit\n---\nTRIPARTY_CROSS_AUDIT_COMPLETE\n",
            "gemini-cross-audit.md": "---\nparty: Gemini\nstage: cross-audit\n---\nTRIPARTY_CROSS_AUDIT_COMPLETE\n",
        }
        for name, text in artifacts.items():
            (run_dir / name).write_text(text, encoding="utf-8", newline="\n")
        state = {
            "true_triparty_ready": True,
            "conclusion": "Ready for true tri-party synthesis",
            "parties": {
                "claude": {
                    "review_sha256": hashlib.sha256(artifacts["claude-review.md"].encode()).hexdigest(),
                    "cross_audit_sha256": hashlib.sha256(artifacts["claude-cross-audit.md"].encode()).hexdigest(),
                },
                "gemini": {
                    "review_sha256": hashlib.sha256(artifacts["gemini-review.md"].encode()).hexdigest(),
                    "cross_audit_sha256": hashlib.sha256(artifacts["gemini-cross-audit.md"].encode()).hexdigest(),
                },
            },
        }
        (run_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
        tri_checkpoint = run(
            [
                str(SCRIPT_DIR / "checkpoint.py"),
                "--root",
                str(tri_root),
                "--workstream",
                "tri-self-test",
                "--active-goal",
                "verify tri-party evidence gate",
                "--decision",
                "Tri-party artifacts are complete",
                "--triparty-run-dir",
                str(run_dir),
            ]
        )
        assert json.loads(tri_checkpoint.stdout)["ok"] is True
        tri_state = json.loads((tri_root / ".agent" / "continuity" / "current.yml").read_text(encoding="utf-8"))
        assert tri_state["gates"]["review_status"] == "passed"

        partial_root = root / "tri-partial"
        partial_run = root / "triparty-partial"
        partial_run.mkdir()
        (partial_run / "claude-review.md").write_text("---\nparty: Claude\nstage: review\n---\nno marker\n", encoding="utf-8")
        partial_checkpoint = run(
            [
                str(SCRIPT_DIR / "checkpoint.py"),
                "--root",
                str(partial_root),
                "--workstream",
                "tri-partial-test",
                "--active-goal",
                "verify partial tri-party evidence gate",
                "--decision",
                "Tri-party artifacts are incomplete",
                "--triparty-run-dir",
                str(partial_run),
            ]
        )
        assert json.loads(partial_checkpoint.stdout)["ok"] is True
        partial_state = json.loads((partial_root / ".agent" / "continuity" / "current.yml").read_text(encoding="utf-8"))
        assert partial_state["gates"]["review_status"] == "partial"

        cwd = Path.cwd()
        try:
            os.chdir(root)
            cwd_run = root / "cwd-only-run"
            cwd_run.mkdir()
            for name, text in artifacts.items():
                (cwd_run / name).write_text(text, encoding="utf-8", newline="\n")
            (cwd_run / "state.json").write_text(json.dumps(state), encoding="utf-8")
            relative_root = root / "relative-root"
            relative_checkpoint = run(
                [
                    str(SCRIPT_DIR / "checkpoint.py"),
                    "--root",
                    str(relative_root),
                    "--workstream",
                    "relative-triparty-test",
                    "--active-goal",
                    "relative triparty path must resolve under root",
                    "--triparty-run-dir",
                    "cwd-only-run",
                ]
            )
            assert json.loads(relative_checkpoint.stdout)["ok"] is True
            relative_state = json.loads((relative_root / ".agent" / "continuity" / "current.yml").read_text(encoding="utf-8"))
            assert relative_state["gates"]["review_status"] == "partial"
        finally:
            os.chdir(cwd)
    print(json.dumps({"ok": True, "tested": ["source-model-and-high-context-transfer", "checkpoint", "validate", "bootstrap", "targeted-handoff", "context-guard", "compaction-false-positive", "explicit-compaction", "rollover-request", "thread-receipt", "receipt-requires-request", "receipt-rejects-stale-request", "redact", "tamper", "active-lock", "credential-url", "triparty-gate", "relative-triparty"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
