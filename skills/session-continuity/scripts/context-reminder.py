"""Notify at 80% context or request a checkpoint in the current chat."""

import json
import locale
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple
from uuid import UUID


THRESHOLD_PERCENT = 80
CHECKPOINT_INSTRUCTION = (
    "Use $session-continuity to save and validate a checkpoint in this chat. Preserve all active user requests. "
    "Use the language requested by the user or used in the source conversation. Compare with the latest real "
    "usage before suggesting a move. If compaction has reduced usage, continue here. Complete minor edits here. "
    "For longer work, distinguish a bounded side task from a necessary move of the entire remaining workstream. "
    "Before creating any user-visible chat, confirm whether the user wants that specific chat and which model "
    "to use, or whether they want the agent to choose. Reuse prior explicit authorization that covers the same "
    "task scope and the model choice. The checkpoint preference and a generic 'continue' or '继续' grant neither "
    "creation nor archive permission. Reuse a matching destination if one already exists. For a full transfer, "
    "verify destination takeover before offering to archive the source when needed. For a side task, keep the "
    "source active, merge the results, and consider archiving the side chat only once the parent task is complete "
    "or under the user's explicit cleanup instructions. Archive a chat only within the user's consent."
)
TAIL_SIZES = (128 * 1024, 2 * 1024 * 1024, 16 * 1024 * 1024)
RESET_RECORD = re.compile(
    rb'^\{\s*(?:"timestamp"\s*:\s*"[^"]*"\s*,\s*)?"type"\s*:\s*"compacted"'
)


class Sample(NamedTuple):
    used: int
    window: int
    offset: int

    @property
    def high(self) -> bool:
        return self.used * 100 >= self.window * THRESHOLD_PERCENT


def parse_sample(line: bytes, offset: int) -> Sample | None:
    header = line[:256]
    if RESET_RECORD.match(header):
        return Sample(0, 1, offset)
    if b'"event_msg"' not in header or not (b'"token_count"' in header or b'"context_compacted"' in header):
        return None
    try:
        record = json.loads(line)
        event = record.get("payload") or {}
        if record.get("type") != "event_msg":
            return None
        if event.get("type") == "context_compacted":
            return Sample(0, 1, offset)
        if event.get("type") != "token_count":
            return None
        info = event.get("info") or {}
        used = (info.get("last_token_usage") or {}).get("total_tokens")
        window = info.get("model_context_window")
        if type(used) is int and type(window) is int and used >= 0 and window > 0:
            return Sample(used, window, offset)
    except (AttributeError, ValueError, UnicodeDecodeError):
        pass
    return None


def recent_sample(path: Path) -> Sample | None:
    with path.open("rb") as transcript:
        size = transcript.seek(0, os.SEEK_END)
        for tail_size in TAIL_SIZES:
            start = max(0, size - tail_size)
            transcript.seek(start)
            data = transcript.read(size - start)
            first_line, *other_lines = data.split(b"\n")
            lines = other_lines if start else [first_line, *other_lines]
            end = size
            for line in reversed(lines):
                offset = end - len(line)
                end = offset - 1
                sample = parse_sample(line, offset)
                if sample:
                    return sample
            if start == 0:
                break
    return None


def latest_context(path: Path) -> tuple[int, int] | None:
    """Return the most recent used/window pair, preserving the original probe interface."""
    sample = recent_sample(path)
    return (sample.used, sample.window) if sample else None


def evidence(thread_id: str, sample: Sample) -> dict:
    return {"session_id": thread_id, "used": sample.used, "window": sample.window,
            "offset": sample.offset, "observed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def save_evidence(path: Path, snapshot: dict) -> bool:
    """Publish the complete record once even if two hook processes finish together."""
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        temp_path = Path(tmp.name)
        tmp.write(json.dumps(snapshot).encode("ascii"))
    try:
        # Windows rename fails if the destination exists. POSIX link has the same semantics.
        if os.name == "nt":
            temp_path.rename(path)
        else:
            os.link(temp_path, path)
        return True
    except FileExistsError:
        return False
    finally:
        temp_path.unlink(missing_ok=True)


def claim(path: Path) -> bool:
    try:
        path.touch(exist_ok=False)
        return True
    except FileExistsError:
        return False


def is_subagent_transcript(path: Path) -> bool:
    # Some clients provide the child's own session ID and rollout rather than a hook flag.
    with path.open("rb") as transcript:
        header = transcript.readline(1024 * 1024)
    try:
        record = json.loads(header)
    except (UnicodeDecodeError, ValueError):
        return True  # Unknown owner. Do not initiate a transfer.
    if record.get("type") != "session_meta":
        return False
    meta = record.get("payload") or {}
    source = meta.get("source")
    return bool(meta.get("parent_thread_id") and meta.get("agent_path")) or (
        isinstance(source, dict) and "subagent" in source
    )


def auto_checkpoint_enabled(hooks: Path) -> bool:
    try:
        settings = json.loads((hooks / "session-continuity.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return False
    return isinstance(settings, dict) and settings.get(
        "auto_checkpoint_at_80", settings.get("auto_handoff_at_80")
    ) is True


def chinese_ui() -> bool:
    language = next((os.environ[key] for key in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG")
                     if os.environ.get(key)), None)
    return (language or locale.getlocale()[0] or "").lower().startswith(("zh", "chinese"))


def checkpoint_output(event: str, snapshot: dict) -> dict:
    percent = snapshot["used"] / snapshot["window"]
    out = {"systemMessage": f"主对话上下文已用 {percent:.1%}，正在保存进度。" if chinese_ui()
           else f"This chat used {percent:.1%} of its context. Saving a checkpoint."}
    instruction = (
        f"Verified token_count for source chat {snapshot['session_id']} at byte offset {snapshot['offset']} "
        f"in its own rollout: {snapshot['used']}/{snapshot['window']} tokens, observed {snapshot['observed_utc']}. "
        "This was the latest actual sample at the time of this check. "
        + CHECKPOINT_INSTRUCTION
    )
    if event == "Stop":
        out.update(decision="block", reason=instruction)
    else:
        out["hookSpecificOutput"] = {"hookEventName": event, "additionalContext": instruction}
    return out


def reminder(payload: dict, codex_home: Path) -> dict | None:
    if payload.get("subagent"):
        return None
    transcript_path = payload.get("transcript_path")
    if not isinstance(transcript_path, str) or not transcript_path:
        return None
    try:
        thread_id = str(UUID(payload.get("session_id") or ""))
    except (AttributeError, ValueError):
        return None

    transcript = Path(transcript_path).resolve()
    if not transcript.is_relative_to((codex_home / "sessions").resolve()):
        return None
    if not transcript.name.endswith(f"-{thread_id}.jsonl"):
        return None
    sample = recent_sample(transcript)
    hooks = codex_home / "hooks"
    marker = hooks / "context-reminder-state" / thread_id
    pending = marker.with_suffix(".pending")
    delivered = marker.with_suffix(".handoff")
    high = sample is not None and sample.high
    if not high:
        # A prior crossing (including a valid pre-compaction marker) cannot trigger a later prompt.
        pending.unlink(missing_ok=True)
        if sample is not None:
            marker.unlink(missing_ok=True)
            delivered.unlink(missing_ok=True)
        return None
    if is_subagent_transcript(transcript):
        return None

    if not auto_checkpoint_enabled(hooks):
        pending.unlink(missing_ok=True)
        marker.parent.mkdir(parents=True, exist_ok=True)
        if claim(marker):
            percent = min(sample.used / sample.window, 1)
            message = (f"此对话已使用模型上下文窗口的 {percent:.1%}。需要时可用 $session-continuity 保存进度。"
                       if chinese_ui() else
                       f"This chat used {percent:.1%} of its context window. Use $session-continuity to save your progress.")
            return {"systemMessage": message}
        return None

    event = payload.get("hook_event_name")
    if event not in {"PreCompact", "UserPromptSubmit", "PostToolUse", "Stop", "SessionStart"}:
        return None
    if event == "SessionStart" and payload.get("source") != "compact":
        return None
    marker.parent.mkdir(parents=True, exist_ok=True)
    if event == "PreCompact" or (event == "Stop" and payload.get("stop_hook_active")):
        # Retain the observation. The next eligible event independently checks current usage.
        if not delivered.exists():
            save_evidence(pending, evidence(thread_id, sample))
        return None
    snapshot = evidence(thread_id, sample)
    if not save_evidence(delivered, snapshot):
        return None
    pending.unlink(missing_ok=True)
    return checkpoint_output(event, snapshot)


def main() -> None:
    codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    try:
        payload = json.load(sys.stdin)
        result = reminder(payload, codex_home)
    except (AttributeError, OSError, TypeError, ValueError):
        return
    if result:
        print(json.dumps(result))


if __name__ == "__main__":
    main()
