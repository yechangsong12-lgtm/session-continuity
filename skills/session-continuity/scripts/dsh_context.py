"""Read an identified DeepSeek Harness v4 JSONL snapshot without opening a session."""

import argparse
import json
from pathlib import Path
import sys


def route(data):
    if not isinstance(data, dict):
        return None
    provider, model = data.get("provider"), data.get("model")
    if all(isinstance(value, str) and value.strip() for value in (provider, model)):
        return provider, model
    return None


def input_tokens(data):
    usage = data.get("usage")
    if usage is None:
        for item in reversed(data.get("stream", [])):
            chunk = item.get("chunk", {}) if item.get("type") == "chunk" else {}
            if chunk.get("type") == "usage":
                usage = chunk.get("usage")
                break
    if not isinstance(usage, dict):
        return None
    counts = [usage.get("inputTokens"), usage.get("cacheReadTokens", 0), usage.get("cacheWriteTokens", 0)]
    if all(type(n) is int and n >= 0 for n in counts):
        return sum(counts)
    return None


def read_snapshot(lines, session_id):
    header = json.loads(next(lines, "null"))
    if not isinstance(header, dict) or header.get("type") != "session" or header.get("version") != 4:
        raise ValueError("Expected an uncompressed DeepSeek Harness v4 session JSONL file.")
    if header.get("id") != session_id:
        raise ValueError("The log belongs to a different session.")
    if header.get("delegationDepth", 0) != 0:
        raise ValueError("Select the top-level source chat, rather than a delegated agent.")

    in_seed = header.get("isSeeded") is True
    actual = capacity_route = pending = None
    window = used = sample_seq = previous_seq = None
    for raw in lines:
        record = json.loads(raw)
        seq = record.get("seq")
        if type(seq) is not int or seq < 0 or (previous_seq is None and seq > 1) or (
            previous_seq is not None and seq != previous_seq + 1
        ):
            raise ValueError("Session event sequence is incomplete.")
        previous_seq = seq
        kind, data = record.get("type"), record.get("data")
        if not isinstance(data, dict) or not isinstance(kind, str):
            raise ValueError("Invalid session event.")
        if kind == "session/end-seed":
            # An inherited prefix can include the parent's earlier end-seed marker.
            actual = capacity_route = pending = window = used = sample_seq = None
            if data.get("inherited") is True:
                in_seed = False
            continue
        if in_seed:
            continue
        if kind == "model/selection":
            pending = route(data)
            actual = used = sample_seq = None
        elif kind == "request/header":
            actual = route((data.get("header") or {}).get("config"))
            if actual == pending:
                pending = None
            used = sample_seq = None
        elif kind == "request/context":
            capacity_route = route(data)
            capacity = data.get("contextWindow")
            window = capacity if type(capacity) is int and capacity > 0 else None
            used = sample_seq = None
        elif (kind.startswith("compaction/") or kind in {"step/start", "turn/start", "llm/retry-started"}
              or isinstance(record.get("surfaceOp"), dict)):
            used = sample_seq = None
        elif kind in {"assistant/attempt", "assistant/message"}:
            used = input_tokens(data) if kind == "assistant/message" and not data.get("interrupted") else None
            sample_seq = seq if used is not None else None

    active = actual if pending is None and actual is not None and actual == capacity_route else None
    measured = active is not None and window is not None and used is not None
    return {
        "session_id": session_id,
        "provider": active[0] if active else None,
        "model": active[1] if active else None,
        "input_tokens": used if measured else None,
        "context_window": window if active else None,
        "sample_seq": sample_seq if measured else None,
        "at_or_above_80": 100 * used >= 80 * window if measured else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, type=Path, help="Uncompressed v4 JSONL for one source chat.")
    parser.add_argument("--session-id", required=True, help="Source ID independently obtained from DSH.")
    args = parser.parse_args()
    try:
        with args.log.open(encoding="utf-8-sig") as lines:
            result = read_snapshot(lines, args.session_id)
    except (ValueError, OSError, TypeError, AttributeError) as exc:
        # Avoid echoing any conversation content from a broken record.
        if type(exc) is ValueError:
            parser.exit(1, f"{exc}\n")
        parser.exit(1, "Unable to read the selected v4 session log.\n")
    json.dump(result, sys.stdout, ensure_ascii=True)
    print()


if __name__ == "__main__":
    main()
