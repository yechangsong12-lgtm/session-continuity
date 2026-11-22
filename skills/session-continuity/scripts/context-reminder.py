"""Show a one-time Codex warning when the current chat reaches 80% context."""

import json
import os
import re
import sys
from pathlib import Path
from uuid import UUID


THRESHOLD_PERCENT = 80
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
    if sample is None:
        return None

    used, window = sample
    marker = codex_home / "hooks" / "context-reminder-state" / thread_id
    if used * 100 < window * THRESHOLD_PERCENT:
        marker.unlink(missing_ok=True)
        return None

    marker.parent.mkdir(parents=True, exist_ok=True)
    try:
        marker.touch(exist_ok=False)
    except FileExistsError:
        return None

    percent = min(used / window, 1)
    return {
        "systemMessage": (
            f"此对话已使用模型上下文窗口的 {percent:.1%}。需要接续时，"
            "发送「用 $session-continuity 交接到新对话」。"
        )
    }


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
