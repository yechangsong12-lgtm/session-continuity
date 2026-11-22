"""Notify at 80% context, or start the user's opted-in session handoff."""

import json
import os
import re
import sys
from pathlib import Path
from uuid import UUID


THRESHOLD_PERCENT = 80
HANDOFF_INSTRUCTION = (
    "主对话已触发用户设置的 80% 自动交接。按 $session-continuity 在当前工作区保存并验证交接，"
    "延续用户最新目标、约束与暂停指示。先核对当前源对话的已有交接和回执，复用已有接手对话。"
    "需要新建时把已验证的交接提示交给新的独立主对话，等它确认读到正确版本并能说明第一步。"
    "确认接手后，在本源对话展示接手对话并询问用户是否归档本源对话，仅在用户明确同意后归档。"
    "若当前环境无法完成交接，保留本对话并说明尚缺的步骤。"
)
TAIL_SIZES = (128 * 1024, 2 * 1024 * 1024, 16 * 1024 * 1024)
RESET_RECORD = re.compile(
    rb'^\{\s*(?:"timestamp"\s*:\s*"[^"]*"\s*,\s*)?"type"\s*:\s*"compacted"'
)


def latest_context(path: Path) -> tuple[int, int] | None:
    """Return (used, window), or (0, 1) after an observed context reset."""
    with path.open("rb") as transcript:
        size = transcript.seek(0, os.SEEK_END)
        for tail_size in TAIL_SIZES:
            start = max(0, size - tail_size)
            transcript.seek(start)
            data = transcript.read(size - start)
            first_line, *other_lines = data.split(b"\n")
            lines = other_lines if start else [first_line, *other_lines]
            for line in reversed(lines):
                header = line[:256]
                if RESET_RECORD.match(header):
                    return (0, 1)
                if b'"event_msg"' not in header:
                    continue
                if b'"token_count"' not in header and b'"context_compacted"' not in header:
                    continue
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if record.get("type") != "event_msg":
                    continue
                event = record.get("payload") or {}
                if event.get("type") == "context_compacted":
                    return (0, 1)
                if event.get("type") != "token_count":
                    continue
                info = event.get("info") or {}
                used = (info.get("last_token_usage") or {}).get("total_tokens")
                window = info.get("model_context_window")
                if type(used) is int and type(window) is int and used >= 0 and window > 0:
                    return (used, window)
            if start == 0:
                break
    return None


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


def auto_handoff_enabled(hooks: Path) -> bool:
    try:
        settings = json.loads((hooks / "session-continuity.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return False
    return isinstance(settings, dict) and settings.get("auto_handoff_at_80") is True


def handoff_output(event: str) -> dict:
    out = {"systemMessage": "主对话已达到 80% 上下文阈值，开始准备交接。"}
    if event == "Stop":
        out.update(decision="block", reason=HANDOFF_INSTRUCTION)
    else:
        out["hookSpecificOutput"] = {"hookEventName": event, "additionalContext": HANDOFF_INSTRUCTION}
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
    sample = latest_context(transcript)
    hooks = codex_home / "hooks"
    marker = hooks / "context-reminder-state" / thread_id
    pending = marker.with_suffix(".pending")
    delivered = marker.with_suffix(".handoff")
    high = sample is not None and sample[0] * 100 >= sample[1] * THRESHOLD_PERCENT
    if (high or pending.exists()) and is_subagent_transcript(transcript):
        return None
    if sample is not None and not high:
        marker.unlink(missing_ok=True)
        if delivered.exists():
            pending.unlink(missing_ok=True)
            delivered.unlink(missing_ok=True)

    if not auto_handoff_enabled(hooks):
        pending.unlink(missing_ok=True)
        if not high:
            return None
        marker.parent.mkdir(parents=True, exist_ok=True)
        if claim(marker):
            percent = min(sample[0] / sample[1], 1)
            return {"systemMessage": f"此对话已使用模型上下文窗口的 {percent:.1%}。需要接续时，发送「用 $session-continuity 交接到新对话」。"}
        return None

    event = payload.get("hook_event_name")
    if event not in {"PreCompact", "UserPromptSubmit", "PostToolUse", "Stop", "SessionStart"}:
        return None
    if event == "SessionStart" and payload.get("source") != "compact":
        return None
    if not high and not pending.exists():
        return None
    marker.parent.mkdir(parents=True, exist_ok=True)
    if event == "PreCompact" or (event == "Stop" and payload.get("stop_hook_active")):
        # PreCompact cannot inject model instructions. Keep the crossing through compaction.
        if high and not delivered.exists():
            claim(pending)
        return None
    if high:
        if not claim(delivered):
            return None
        pending.unlink(missing_ok=True)
    else:
        # Only one event may consume a pending crossing after the usage has dropped.
        try:
            pending.unlink()
        except FileNotFoundError:
            return None
    return handoff_output(event)


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
