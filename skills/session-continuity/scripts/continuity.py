#!/usr/bin/env python3
"""Session continuity checkpoint/resume utilities.

The state file is JSON written to current.yml. JSON is valid YAML 1.2, avoids a
PyYAML dependency, and keeps validation deterministic on minimal Python installs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import textwrap
import tempfile
from pathlib import Path
from typing import Any


SCHEMA = "codex-session-continuity/v1"
DEFAULT_DIR = Path(".agent") / "continuity"
HASHED_FILES = ("current.yml", "handoff.md", "bootstrap.md", "events.jsonl")
ROLLOVER_REQUEST = "rollover-request.json"
THREAD_RECEIPT = "thread-receipt.json"
ROLLOVER_REQUEST_SCHEMA = "codex-session-continuity/rollover-request/v1"
THREAD_RECEIPT_SCHEMA = "codex-session-continuity/thread-receipt/v1"
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(bearer\s+)[a-z0-9._~+/=-]{20,}"),
    re.compile(r"(?i)\b([a-z0-9_]*(?:database_url|redis_url|mongo_uri|dsn|uri|url)[a-z0-9_]*\s*[:=]\s*)[\"']?[a-z][a-z0-9+.-]*://[^\"'\s]*:[^\"'\s@]+@[^\"'\s]+[\"']?"),
    re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s:@]+:[^@\s]+@"),
    re.compile(r"(?i)\b([a-z0-9_]*(?:api[_-]?key|token|secret|password)[a-z0-9_]*\s*[:=]\s*)[\"']?[a-z0-9._~+/=-]{12,}[\"']?"),
    re.compile(r"(?i)\b(openai|anthropic|gemini|google|github|figma|slack|aws|secret|token|api[_-]?key)([_-]?[a-z0-9]*)?\s*[:=]\s*[\"']?([a-z0-9._~+/=-]{12,})"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b"),
    re.compile(r"(?i)([?&](access_token|token|api_key|signature|secret)=)[^&\s]+"),
    re.compile(r"(?i)\b(cookie:\s*)[^\n\r]+"),
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return slug[:80] or "target"


def continuity_dir(root: Path, target: str = "") -> Path:
    if target:
        return root / DEFAULT_DIR / "targets" / slugify(target)
    return root / DEFAULT_DIR


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
        try:
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
        except OSError:
            dir_fd = None
        if dir_fd is not None:
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def redact_text(text: str) -> tuple[str, int]:
    redacted = text
    count = 0
    for pattern in SECRET_PATTERNS:
        redacted, n = pattern.subn(lambda m: _replacement(m), redacted)
        count += n
    return redacted, count


def _replacement(match: re.Match[str]) -> str:
    if match.re.pattern.startswith("(?i)\\b(bearer"):
        return match.group(1) + "[REDACTED]"
    if "(?:database_url" in match.re.pattern:
        return match.group(1) + "[REDACTED_URL]"
    if "[a-z][a-z0-9+.-]*://" in match.re.pattern:
        return match.group(1) + "[REDACTED]@"
    if "(?:api" in match.re.pattern:
        return match.group(1) + "[REDACTED]"
    if "([?&]" in match.re.pattern:
        return match.group(1) + "[REDACTED]"
    if "cookie" in match.re.pattern.lower():
        return match.group(1) + "[REDACTED]"
    if "PRIVATE KEY" in match.group(0):
        return "[REDACTED_PRIVATE_KEY]"
    prefix = match.group(0).split("=", 1)[0].split(":", 1)[0]
    if prefix and len(prefix) < 80 and ("=" in match.group(0) or ":" in match.group(0)):
        sep = "=" if "=" in match.group(0) else ":"
        return f"{prefix}{sep}[REDACTED]"
    return "[REDACTED_SECRET]"


def scan_for_secrets(text: str) -> list[str]:
    findings: list[str] = []
    for idx, pattern in enumerate(SECRET_PATTERNS, start=1):
        if pattern.search(text):
            findings.append(f"secret_pattern_{idx}")
    return findings


def load_current(cdir: Path) -> dict[str, Any] | None:
    path = cdir / "current.yml"
    if not path.exists():
        return None
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid current.yml JSON-compatible YAML: {exc}") from exc


def probe_writer(pid: int) -> None:
    """Raise OSError for an unavailable writer without signaling it on Windows."""
    if os.name != "nt":
        os.kill(pid, 0)
        return
    import _winapi

    try:
        handle = _winapi.OpenProcess(_winapi.SYNCHRONIZE, False, pid)
    except PermissionError:
        # A protected process exists but cannot be queried by this user.
        return
    try:
        if _winapi.WaitForSingleObject(handle, 0) != _winapi.WAIT_TIMEOUT:
            raise ProcessLookupError(pid)
    finally:
        _winapi.CloseHandle(handle)


def acquire_lock(cdir: Path, force: bool = False) -> Path:
    lock_dir = cdir / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock = lock_dir / "writer.lock"
    if lock.exists():
        age = dt.datetime.now().timestamp() - lock.stat().st_mtime
        owner_alive = False
        try:
            owner = json.loads(read_text(lock))
            owner_pid = int(owner.get("pid") or 0)
            if owner_pid > 0:
                probe_writer(owner_pid)
                owner_alive = True
        except (OSError, ValueError, json.JSONDecodeError):
            owner_alive = False
        if not force and owner_alive and age < 900:
            raise SystemExit(f"Active writer lock exists: {lock}")
        if force or age >= 900 or not owner_alive:
            lock.unlink()
    fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps({"pid": os.getpid(), "created_at": utc_now()}, indent=2))
    return lock


def active_writer_lock(cdir: Path, *, allow_current_pid: bool = True) -> str | None:
    lock = cdir / "locks" / "writer.lock"
    if not lock.exists():
        return None
    age = dt.datetime.now().timestamp() - lock.stat().st_mtime
    try:
        owner = json.loads(read_text(lock))
        owner_pid = int(owner.get("pid") or 0)
    except (ValueError, json.JSONDecodeError):
        owner_pid = 0
    if allow_current_pid and owner_pid == os.getpid():
        return None
    if owner_pid > 0:
        try:
            probe_writer(owner_pid)
            return str(lock)
        except OSError:
            return str(lock) if age < 900 else None
    if age < 900:
        return str(lock)
    return None


def release_lock(lock: Path) -> None:
    try:
        lock.unlink()
    except FileNotFoundError:
        pass


def git_changed_files(root: Path) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "status", "--short"],
            cwd=root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return []
    files: list[str] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return sorted(set(files))


def triparty_artifact_status(path: Path, marker: str, expected_party: str, expected_stage: str) -> str:
    if not path.exists():
        return "missing"
    if path.stat().st_size == 0:
        return "empty"
    try:
        text = read_text(path)
    except UnicodeDecodeError:
        return "unreadable"
    if marker not in text:
        return "incomplete"
    if f"party: {expected_party}" not in text or f"stage: {expected_stage}" not in text:
        return "wrong_metadata"
    return "completed"


def triparty_state_gate(run_dir: Path) -> tuple[str, str]:
    state_path = run_dir / "state.json"
    merge_path = run_dir / "merge-status.md"
    conclusion = ""
    if state_path.exists():
        try:
            state = json.loads(read_text(state_path))
        except json.JSONDecodeError:
            return "invalid", conclusion
        conclusion = str(state.get("conclusion") or "")
        if state.get("true_triparty_ready") is True:
            parties = state.get("parties", {})
            expected_hashes = {
                "claude-review.md": parties.get("claude", {}).get("review_sha256"),
                "gemini-review.md": parties.get("gemini", {}).get("review_sha256"),
                "claude-cross-audit.md": parties.get("claude", {}).get("cross_audit_sha256"),
                "gemini-cross-audit.md": parties.get("gemini", {}).get("cross_audit_sha256"),
            }
            for name, expected in expected_hashes.items():
                path = run_dir / name
                if not expected:
                    return "missing_hash", conclusion
                if not path.exists():
                    return "missing_artifact_for_hash", conclusion
                if sha256_file(path) != expected:
                    return "hash_mismatch", conclusion
            return "completed", conclusion
        return "partial", conclusion
    if merge_path.exists():
        text = read_text(merge_path)
        match = re.search(r"^Conclusion label:\s*(.+)$", text, re.MULTILINE)
        conclusion = match.group(1).strip() if match else ""
        if conclusion == "Ready for true tri-party synthesis":
            return "completed", conclusion
        return "partial", conclusion
    return "missing", conclusion


def normalize_list(values: list[str] | None) -> list[str]:
    clean: list[str] = []
    for value in values or []:
        value = value.strip()
        if value:
            clean.append(value)
    return clean


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def resolve_against_root(value: str, root: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def use_chinese_for_handoff(state: dict[str, Any]) -> bool:
    texts = (state.get("latest_user_request", ""), state.get("active_goal", {}).get("objective", ""))
    return any(re.search(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", text or "") for text in texts)


def build_handoff(state: dict[str, Any]) -> str:
    target = state.get("target") or ""
    chinese = use_chinese_for_handoff(state)
    active = state.get("active_goal", {})
    statuses = {
        "in_progress": "进行中", "complete": "已完成", "completed": "已完成", "blocked": "受阻",
        "passed": "通过", "partial": "部分完成", "not_required": "无需复核",
        "ready": "就绪", "failed": "失败", "pending": "待核验",
    } if chinese else {}

    goal_status = active.get("status", "")
    lines = [
        "# 会话交接摘要" if chinese else "# Session Continuity Handoff",
        "",
        f"- {'任务名称　' if chinese else 'Workstream: '}{state.get('workstream', '')}",
    ]
    if target:
        lines.append(f"- {'交接范围　' if chinese else 'Target: '}{target}")
    lines.extend([
        f"- {'修订号　' if chinese else 'Revision: '}{state.get('revision', '')}",
        f"- {'更新时间　' if chinese else 'Updated: '}{state.get('updated_at', '')}",
        f"- {'用户最新要求　' if chinese else 'Latest request: '}{state.get('latest_user_request', '')}",
        f"- {'当前目标　' if chinese else 'Active goal: '}{active.get('objective', '')}",
        f"- {'进度　' if chinese else 'Goal status: '}{statuses.get(goal_status, goal_status)}",
        "",
        "## 校验结果" if chinese else "## Gates",
        "",
    ])
    checks = {
        "probe_status": "文件可读性", "redaction_status": "敏感信息检查",
        "hash_status": "文件完整性", "review_status": "复核", "bootstrap_status": "接续提示",
    } if chinese else {}
    for key, value in state.get("gates", {}).items():
        lines.append(f"- {checks.get(key, key)}{'　' if chinese else ': '}{statuses.get(value, value)}")
    lines.extend(["", "## 已作决定与依据" if chinese else "## Decisions", ""])
    empty = "- 暂无记录。" if chinese else "- None recorded."
    decisions = state.get("decisions", [])
    if decisions:
        for item in decisions:
            lines.append(f"- [{item.get('source', 'codex')}] {item.get('text', '')}")
            if item.get("evidence"):
                lines.append(f"  - {'依据　' if chinese else 'Evidence: '}{item['evidence']}")
    else:
        lines.append(empty)
    lines.extend(["", "## 待办事项" if chinese else "## Open Tasks", ""])
    tasks = state.get("open_tasks", [])
    if tasks:
        lines.extend(f"- {task}" for task in tasks)
    else:
        lines.append(empty)
    lines.extend(["", "## 阻塞项" if chinese else "## Blocked Items", ""])
    blocked = state.get("blocked_items", [])
    if blocked:
        lines.extend(f"- {item}" for item in blocked)
    else:
        lines.append(empty)
    changed_files = state.get("changed_files") or []
    if changed_files:
        lines.extend(["", "## 改动文件" if chinese else "## Changed Files", ""])
        lines.extend(f"- `{path}`" for path in changed_files)
    lines.extend(["", "## 接手时读取" if chinese else "## Context To Load", ""])
    for item in state.get("context_to_load", []):
        lines.append(f"- `{item}`")
    lines.append("")
    return "\n".join(lines)


def build_bootstrap(state: dict[str, Any]) -> str:
    gates = state.get("gates", {})
    workspace_root = state.get("workspace_root") or "<workspace-root>"
    target = state.get("target") or ""
    validator = Path(__file__).resolve().with_name("validate.py")
    arguments = [sys.executable, "-B", "-X", "utf8", str(validator), "--root", workspace_root]
    if target:
        arguments.extend(["--target", target])
    if os.name == "nt":
        # PowerShell also recognizes typographic single quotes as delimiters.
        def quote_argument(value: str) -> str:
            return "'" + re.sub("['\u2018\u2019\u201a\u201b]", lambda match: "'" + match[0], value) + "'"

        language = "powershell"
        command = "& " + " ".join(quote_argument(arg) for arg in arguments)
    else:
        language = "sh"
        command = shlex.join(arguments)
    state_dir = f".agent/continuity/targets/{target}" if target else ".agent/continuity"
    active = state.get("active_goal", {})
    chinese = use_chinese_for_handoff(state)
    if chinese:
        lines = [
            "# 接续当前任务", "",
            f"从 `{state_dir}/current.yml` 和 `{state_dir}/handoff.md` 读取已保存的工作状态。",
            "", f"工作区　{workspace_root}",
        ]
        if target:
            lines.append(f"交接范围　{target}")
        lines.extend([
            f"任务名称　{state.get('workstream', '')}",
            f"修订号　{state.get('revision', '')}",
            f"用户最新要求　{state.get('latest_user_request', '')}",
            f"当前目标　{active.get('objective', '')}",
            f"进度标记　`{active.get('status', '')}`",
            "", "## 接手步骤", "", "1. 在指定工作区运行以下命令，核验交接包。",
        ])
        after_check = [
            "2. 如校验失败或修订号与上文不同，请先在本对话报告具体问题。",
            f"3. 校验通过后，阅读 `{state_dir}/handoff.md`。回查第一项待办所依赖的原始资料；任务已完成或受阻时，核实已记录的结果或原因。",
            "4. 在本接手对话中沿用用户在原对话使用的语言，简短确认已核验的修订号、查过的一项依据，以及下一步或最终状态。复核仅部分完成时一并说明。",
            "5. 接着执行已获授权的任务，在本对话报告结果、证据位置和未决事项，供主对话取回。",
        ]
    else:
        lines = [
            "# Resume This Workstream", "",
            f"Load `{state_dir}/current.yml` and `{state_dir}/handoff.md` as the source of truth for this workspace.",
            "", f"Workspace root: {workspace_root}",
        ]
        if target:
            lines.append(f"Target handoff: {target}")
        lines.extend([
            f"Workstream: {state.get('workstream', '')}",
            f"Revision: {state.get('revision', '')}",
            f"Latest user request: {state.get('latest_user_request', '')}",
            f"Active goal: {active.get('objective', '')}",
            f"Goal status: {active.get('status', '')}",
            "", "Required checks before continuing:", "", "1. Validate the saved checkpoint in its workspace.",
        ])
        after_check = [
            "2. If validation fails or the revision differs from the revision above, report the problem here before proceeding.",
            f"3. After validation, read `{state_dir}/handoff.md` and check the source for the first open task, or confirm the recorded completion or blocker.",
            "4. In this destination chat, use the user's language from the source chat. Acknowledge the validated revision, one source you checked, and the next action or final status. Mention partial review when applicable.",
            "5. Continue the authorized work and report results, evidence locations, and open items here so the main chat can retrieve them.",
        ]
    lines.extend(["", f"```{language}", command, "```", "", *after_check])
    if gates.get("hash_status") != "passed" or gates.get("redaction_status") != "passed":
        lines.extend(["", "请先完成交接包校验，再继续任务。" if chinese else "Hard stop: validate the continuity package before resuming."])
    lines.append("")
    return "\n".join(lines)


def write_manifest(cdir: Path, root: Path, state: dict[str, Any]) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for name in HASHED_FILES:
        path = cdir / name
        if path.exists():
            files[name] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    manifest = {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "root": str(root),
        "revision": state.get("revision"),
        "files": files,
    }
    write_text(cdir / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return manifest


def validate_package(root: Path) -> tuple[bool, list[str], dict[str, Any] | None]:
    return validate_package_at(root, "")


def validate_package_at(root: Path, target: str = "") -> tuple[bool, list[str], dict[str, Any] | None]:
    cdir = continuity_dir(root, target)
    errors: list[str] = []
    active_lock = active_writer_lock(cdir)
    if active_lock:
        errors.append(f"active writer lock: {active_lock}")
    state = load_current(cdir)
    if state is None:
        return False, ["missing current.yml"], None
    if state.get("schema") != SCHEMA:
        errors.append(f"schema mismatch: {state.get('schema')}")
    manifest_path = cdir / "manifest.json"
    if not manifest_path.exists():
        errors.append("missing manifest.json")
        manifest = None
    else:
        try:
            manifest = json.loads(read_text(manifest_path))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid manifest.json: {exc}")
            manifest = None
    if manifest:
        for name, meta in manifest.get("files", {}).items():
            path = cdir / name
            if not path.exists():
                errors.append(f"manifest file missing: {name}")
                continue
            actual = sha256_file(path)
            if actual != meta.get("sha256"):
                errors.append(f"hash mismatch: {name}")
    for name in list(HASHED_FILES) + ["manifest.json"]:
        path = cdir / name
        if path.exists():
            findings = scan_for_secrets(read_text(path))
            if findings:
                errors.append(f"possible secret in {name}: {', '.join(findings)}")
    gates = state.setdefault("gates", {})
    if errors:
        gates["probe_status"] = "failed"
        if any("secret" in e for e in errors):
            gates["redaction_status"] = "failed"
        if any("hash mismatch" in e or "manifest" in e for e in errors):
            gates["hash_status"] = "failed"
        if any("active writer lock" in e for e in errors):
            gates["bootstrap_status"] = "blocked"
        return False, errors, state
    return True, [], state


def find_current_session_log(thread_id: str) -> Path | None:
    if not thread_id:
        return None
    candidates: list[Path] = []
    for base in [Path.home() / ".codex" / "sessions", Path.home() / ".codex" / "archived_sessions"]:
        if base.exists():
            candidates.extend(base.rglob(f"rollout-*{thread_id}.jsonl"))
    if not candidates:
        return None
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0]


def parse_session_metrics(session_log: Path, *, large_output_chars: int) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "session_log": str(session_log),
        "session_bytes": session_log.stat().st_size if session_log.exists() else 0,
        "jsonl_lines": 0,
        "invalid_json_lines": 0,
        "tool_calls": 0,
        "tool_outputs": 0,
        "large_tool_outputs": 0,
        "large_log_lines": 0,
        "compaction_markers": 0,
        "token_count_events": 0,
        "latest_input_tokens": None,
        "latest_output_tokens": None,
        "latest_total_tokens": None,
        "model_context_window": None,
        "latest_context_ratio": None,
    }
    latest_info: dict[str, Any] | None = None
    with session_log.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            metrics["jsonl_lines"] += 1
            if len(line) >= large_output_chars:
                metrics["large_log_lines"] += 1
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                metrics["invalid_json_lines"] += 1
                continue
            event_type = event.get("type")
            payload = event.get("payload") or {}
            if event_type == "turn_context":
                if payload.get("compacted") is True or payload.get("context_compacted") is True:
                    metrics["compaction_markers"] += 1
            if event_type == "response_item":
                item_type = payload.get("type")
                if item_type == "function_call":
                    metrics["tool_calls"] += 1
                elif item_type == "function_call_output":
                    metrics["tool_outputs"] += 1
                    output = str(payload.get("output") or "")
                    if len(output) >= large_output_chars:
                        metrics["large_tool_outputs"] += 1
            elif event_type == "event_msg" and payload.get("type") == "token_count":
                metrics["token_count_events"] += 1
                latest_info = payload.get("info") or {}
            elif event_type == "event_msg":
                payload_type = str(payload.get("type") or "").lower()
                if payload_type in {"compaction", "context_compaction", "context_compacted", "compact"}:
                    metrics["compaction_markers"] += 1
    if latest_info:
        usage = latest_info.get("last_token_usage") or {}
        window = latest_info.get("model_context_window")
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        total_tokens = usage.get("total_tokens")
        metrics["latest_input_tokens"] = input_tokens
        metrics["latest_output_tokens"] = output_tokens
        metrics["latest_total_tokens"] = total_tokens
        metrics["model_context_window"] = window
        if isinstance(input_tokens, (int, float)) and isinstance(window, (int, float)) and window > 0:
            metrics["latest_context_ratio"] = input_tokens / window
    return metrics


def context_pressure_eval(args: argparse.Namespace, metrics: dict[str, Any]) -> dict[str, Any]:
    rank = 0
    reasons: list[str] = []
    ratio = metrics.get("latest_context_ratio")
    if args.force_rollover:
        rank = 3
        reasons.append("force_rollover flag is set")
    if isinstance(ratio, (int, float)):
        if ratio >= args.rollover_threshold:
            rank = max(rank, 3)
            reasons.append(f"context ratio {ratio:.2%} >= rollover threshold {args.rollover_threshold:.2%}")
        elif ratio >= args.checkpoint_threshold:
            rank = max(rank, 2)
            reasons.append(f"context ratio {ratio:.2%} >= checkpoint threshold {args.checkpoint_threshold:.2%}")
        elif ratio >= args.warn_threshold:
            rank = max(rank, 1)
            reasons.append(f"context ratio {ratio:.2%} >= watch threshold {args.warn_threshold:.2%}")
    else:
        reasons.append("no token_count event found; using fallback signals only")

    if metrics.get("compaction_markers", 0) > 0:
        rank = max(rank, 3)
        reasons.append("compaction marker found in session log")
    if metrics.get("session_bytes", 0) >= args.bytes_rollover:
        rank = max(rank, 3)
        reasons.append(f"session log bytes >= bytes rollover threshold {args.bytes_rollover}")
    elif metrics.get("session_bytes", 0) >= args.bytes_checkpoint:
        rank = max(rank, 2)
        reasons.append(f"session log bytes >= bytes checkpoint threshold {args.bytes_checkpoint}")
    if metrics.get("large_tool_outputs", 0) >= args.large_output_rollover_count:
        rank = max(rank, 3)
        reasons.append("large tool output count reached rollover threshold")
    elif metrics.get("large_tool_outputs", 0) >= args.large_output_checkpoint_count:
        rank = max(rank, 2)
        reasons.append("large tool output count reached checkpoint threshold")
    if args.large_read_count >= args.large_read_rollover_count:
        rank = max(rank, 3)
        reasons.append("declared large read count reached rollover threshold")
    elif args.large_read_count >= args.large_read_checkpoint_count:
        rank = max(rank, 2)
        reasons.append("declared large read count reached checkpoint threshold")
    if args.before_long_loop and rank >= 1:
        rank = max(rank, 3)
        reasons.append("before_long_loop is set while context pressure is non-zero")
    elif args.before_long_loop:
        rank = max(rank, 2)
        reasons.append("before_long_loop is set")
    if args.phase_boundary or args.major_evidence:
        rank = max(rank, 2)
        reasons.append("phase boundary or major evidence checkpoint requested")
    if args.artifact_count >= args.artifact_checkpoint_count:
        rank = max(rank, 2)
        reasons.append("artifact count reached checkpoint threshold")
    if args.blocked_item:
        rank = max(rank, 2)
        reasons.append("blocked items were declared")

    severity = ["ok", "watch", "checkpoint_recommended", "rollover_required"][rank]
    action = "none"
    if rank == 2:
        action = "checkpoint"
    elif rank >= 3:
        action = "review_in_current_chat"
    return {
        "severity": severity,
        "action": action,
        "rank": rank,
        "reasons": reasons,
        "thresholds": {
            "warn": args.warn_threshold,
            "checkpoint": args.checkpoint_threshold,
            "rollover": args.rollover_threshold,
            "bytes_checkpoint": args.bytes_checkpoint,
            "bytes_rollover": args.bytes_rollover,
        },
    }


def run_checkpoint_for_guard(root: Path, args: argparse.Namespace, evaluation: dict[str, Any], session_log: Path | None) -> dict[str, Any]:
    command = [
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        "checkpoint",
        "--root",
        str(root),
        "--workstream",
        args.workstream or root.name,
        "--latest-user-request",
        args.latest_user_request or "Automatic context rollover guard",
        "--active-goal",
        args.active_goal or "Preserve session state before context pressure becomes unsafe",
        "--decision",
        "; ".join(evaluation.get("reasons") or ["Context guard requested a checkpoint"]),
        "--open-task",
        args.next_task or "Resume from the continuity bootstrap and continue from the handoff.",
        "--source",
        args.source,
    ]
    if args.target:
        command.extend(["--target", args.target])
    for item in normalize_list(args.decision):
        command.extend(["--decision", item])
    for item in normalize_list(args.open_task):
        command.extend(["--open-task", item])
    for item in normalize_list(args.blocked_item):
        command.extend(["--blocked-item", item])
    if session_log:
        command.extend(["--context-file", str(session_log)])
    proc = subprocess.run(command, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result: dict[str, Any] = {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stderr": proc.stderr,
    }
    try:
        result["result"] = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result["stdout"] = proc.stdout
    return result


def write_rollover_request(
    root: Path,
    target: str,
    source_thread_id: str,
    evaluation: dict[str, Any],
    metrics: dict[str, Any],
    checkpoint: dict[str, Any],
    approved_model: str = "",
) -> dict[str, Any]:
    cdir = continuity_dir(root, target)
    ok, errors, state = validate_package_at(root, target)
    bootstrap_path = cdir / "bootstrap.md"
    prompt = read_text(bootstrap_path) if ok and bootstrap_path.exists() else ""
    request = {
        "schema": ROLLOVER_REQUEST_SCHEMA,
        "generated_at": utc_now(),
        "workspace_root": str(root),
        "target": slugify(target) if target else "",
        "source_thread_id": source_thread_id,
        "continuity_dir": str(cdir),
        "bootstrap_path": str(bootstrap_path),
        "status": "ready" if ok else "blocked",
        "thread_action": ("create_thread" if approved_model else "confirm_chat_and_model") if ok else "manual_repair_required",
        "approved_model": approved_model,
        "preferred_target": {"type": "projectless", "directoryName": root.name},
        "requires_codex_thread_tool": "create_thread",
        "validation": {
            "ok": ok,
            "errors": errors,
            "revision": state.get("revision") if state else None,
            "gates": state.get("gates") if state else {},
        },
        "trigger": evaluation,
        "metrics": metrics,
        "checkpoint": checkpoint,
        "prompt": prompt,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    }
    write_text(cdir / ROLLOVER_REQUEST, json.dumps(request, indent=2, ensure_ascii=False) + "\n")
    request["request_sha256"] = sha256_file(cdir / ROLLOVER_REQUEST)
    return request


def command_guard(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    session_log: Path | None = None
    source_thread_id = args.thread_id or os.environ.get("CODEX_THREAD_ID", "")
    if args.session_log:
        session_log = Path(args.session_log).expanduser().resolve()
        if not session_log.exists():
            print(json.dumps({"ok": False, "error": f"missing session log: {session_log}"}, indent=2), file=sys.stderr)
            return 1
    else:
        session_log = find_current_session_log(source_thread_id)
    metrics = parse_session_metrics(session_log, large_output_chars=args.large_output_chars) if session_log else {
        "session_log": "",
        "session_bytes": 0,
        "jsonl_lines": 0,
        "token_count_events": 0,
        "latest_context_ratio": None,
        "model_context_window": None,
        "latest_input_tokens": None,
        "large_tool_outputs": 0,
        "compaction_markers": 0,
    }
    evaluation = context_pressure_eval(args, metrics)
    result: dict[str, Any] = {
        "ok": True,
        "root": str(root),
        "target": slugify(args.target) if args.target else "",
        "thread_id": source_thread_id,
        "session_log": str(session_log) if session_log else "",
        "metrics": metrics,
        "evaluation": evaluation,
        "checkpoint": None,
        "rollover_request": None,
    }
    should_checkpoint = args.checkpoint and evaluation["rank"] >= 2
    if args.force_checkpoint:
        should_checkpoint = True
    if should_checkpoint:
        checkpoint = run_checkpoint_for_guard(root, args, evaluation, session_log)
        result["checkpoint"] = checkpoint
        if not checkpoint.get("ok"):
            result["ok"] = False
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 1
        if evaluation["action"] == "review_in_current_chat" or args.write_request:
            request = write_rollover_request(root, args.target, source_thread_id, evaluation, metrics, checkpoint)
            result["rollover_request"] = {
                "path": str(continuity_dir(root, args.target) / ROLLOVER_REQUEST),
                "status": request["status"],
                "thread_action": request["thread_action"],
                "bootstrap_path": request["bootstrap_path"],
            }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


def command_thread_receipt(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    cdir = continuity_dir(root, args.target)
    request_path = cdir / ROLLOVER_REQUEST
    request: dict[str, Any] | None = None
    request_sha = ""
    if request_path.exists():
        request_sha = sha256_file(request_path)
        try:
            request = json.loads(read_text(request_path))
        except json.JSONDecodeError as exc:
            print(json.dumps({"ok": False, "error": f"invalid rollover request: {exc}"}, indent=2), file=sys.stderr)
            return 1
    ok, errors, state = validate_package_at(root, args.target)
    if not ok:
        print(json.dumps({"ok": False, "errors": errors}, indent=2, ensure_ascii=False), file=sys.stderr)
        return 1
    bootstrap_path = cdir / "bootstrap.md"
    prompt = read_text(bootstrap_path) if bootstrap_path.exists() else ""
    bootstrap_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    status = "created" if args.created_thread_id else "pending_worktree" if args.pending_worktree_id else "manual_required"
    if status != "manual_required":
        request_errors: list[str] = []
        if request is None:
            request_errors.append(f"missing {ROLLOVER_REQUEST}")
        else:
            request_target = slugify(args.target) if args.target else ""
            validation = request.get("validation") if isinstance(request.get("validation"), dict) else {}
            if request.get("schema") != ROLLOVER_REQUEST_SCHEMA:
                request_errors.append("rollover request schema mismatch")
            if request.get("status") != "ready":
                request_errors.append("rollover request is not ready")
            if request.get("thread_action") == "confirm_chat_and_model":
                request_errors.append("new chat and model selection require user confirmation")
            if request.get("workspace_root") != str(root):
                request_errors.append("rollover request workspace root mismatch")
            if request.get("target", "") != request_target:
                request_errors.append("rollover request target mismatch")
            if validation.get("revision") != state.get("revision"):
                request_errors.append("rollover request revision does not match current continuity revision")
            if request.get("prompt_sha256") != bootstrap_sha:
                request_errors.append("rollover request prompt hash does not match current bootstrap")
        if request_errors:
            print(json.dumps({"ok": False, "errors": request_errors}, indent=2, ensure_ascii=False), file=sys.stderr)
            return 1
    receipt = {
        "schema": THREAD_RECEIPT_SCHEMA,
        "recorded_at": utc_now(),
        "workspace_root": str(root),
        "target": slugify(args.target) if args.target else "",
        "source_thread_id": args.source_thread_id or (request or {}).get("source_thread_id", "") or os.environ.get("CODEX_THREAD_ID", ""),
        "created_thread_id": args.created_thread_id,
        "pending_worktree_id": args.pending_worktree_id,
        "thread_url": args.thread_url,
        "tool": args.tool,
        "target_type": args.target_type,
        "status": status,
        "continuity_revision": state.get("revision") if state else None,
        "continuity_gates": state.get("gates") if state else {},
        "bootstrap_path": str(bootstrap_path),
        "bootstrap_sha256": bootstrap_sha,
        "rollover_request_path": str(request_path) if request_path.exists() else "",
        "rollover_request_sha256": request_sha,
        "rollover_request_status": (request or {}).get("status", ""),
        "notes": args.note,
    }
    write_text(cdir / THREAD_RECEIPT, json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "receipt": str(cdir / THREAD_RECEIPT), "status": receipt["status"]}, indent=2, ensure_ascii=False))
    return 0


def command_checkpoint(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    cdir = continuity_dir(root, args.target)
    cdir.mkdir(parents=True, exist_ok=True)
    lock = acquire_lock(cdir, force=args.force_lock)
    try:
        existing = load_current(cdir) or {}
        revision = int(existing.get("revision") or 0) + 1
        redaction_count = 0

        def scrub(value: str) -> str:
            nonlocal redaction_count
            redacted, count = redact_text(value)
            redaction_count += count
            return redacted

        decisions = [
            {"text": scrub(item), "source": args.source, "evidence": scrub(args.evidence or "")}
            for item in normalize_list(args.decision)
        ]
        context_files = [scrub(item) for item in normalize_list(args.context_file)]
        if not context_files:
            state_dir = f".agent/continuity/targets/{slugify(args.target)}" if args.target else ".agent/continuity"
            context_files = [f"{state_dir}/current.yml", f"{state_dir}/handoff.md"]
        changed = sorted(set(scrub(item) for item in (normalize_list(args.changed_file) + git_changed_files(root))))
        triparty = {
            "run_dir": scrub(args.triparty_run_dir or ""),
            "claude_review": "unknown",
            "gemini_review": "unknown",
            "cross_audit": "unknown",
            "state_gate": "unknown",
            "merge_conclusion": "",
        }
        review_status = "not_required"
        if args.triparty_run_dir:
            run_dir = resolve_against_root(args.triparty_run_dir, root)
            triparty["run_dir"] = scrub(str(run_dir))
            triparty["claude_review"] = triparty_artifact_status(run_dir / "claude-review.md", "TRIPARTY_REVIEW_COMPLETE", "Claude", "review")
            triparty["gemini_review"] = triparty_artifact_status(run_dir / "gemini-review.md", "TRIPARTY_REVIEW_COMPLETE", "Gemini", "review")
            claude_cross = triparty_artifact_status(run_dir / "claude-cross-audit.md", "TRIPARTY_CROSS_AUDIT_COMPLETE", "Claude", "cross-audit")
            gemini_cross = triparty_artifact_status(run_dir / "gemini-cross-audit.md", "TRIPARTY_CROSS_AUDIT_COMPLETE", "Gemini", "cross-audit")
            triparty["cross_audit"] = "completed" if claude_cross == "completed" and gemini_cross == "completed" else f"claude={claude_cross};gemini={gemini_cross}"
            state_gate, merge_conclusion = triparty_state_gate(run_dir)
            triparty["state_gate"] = state_gate
            triparty["merge_conclusion"] = merge_conclusion
            required_review_values = [
                triparty["claude_review"],
                triparty["gemini_review"],
                triparty["cross_audit"],
                triparty["state_gate"],
            ]
            review_status = (
                "passed"
                if all(value == "completed" for value in required_review_values)
                else "partial"
            )

        state: dict[str, Any] = {
            "schema": SCHEMA,
            "revision": revision,
            "created_at": existing.get("created_at") or utc_now(),
            "updated_at": utc_now(),
            "workspace_root": str(root),
            "target": slugify(args.target) if args.target else "",
            "target_label": scrub(args.target or ""),
            "workstream": scrub(args.workstream or existing.get("workstream") or root.name),
            "latest_user_request": scrub(args.latest_user_request or existing.get("latest_user_request") or ""),
            "active_goal": {
                "status": args.goal_status,
                "objective": scrub(args.active_goal or existing.get("active_goal", {}).get("objective", "")),
            },
            "decisions": decisions or existing.get("decisions", []),
            "open_tasks": [scrub(item) for item in normalize_list(args.open_task)] or existing.get("open_tasks", []),
            "blocked_items": [scrub(item) for item in normalize_list(args.blocked_item)],
            "changed_files": changed,
            "context_to_load": context_files,
            "gates": {
                "probe_status": "passed",
                "review_status": review_status,
                "redaction_status": "passed" if redaction_count >= 0 else "failed",
                "hash_status": "pending",
                "bootstrap_status": "ready",
            },
            "triparty": triparty,
        }

        current_text = json.dumps(state, indent=2, ensure_ascii=False) + "\n"
        write_text(cdir / "current.yml", current_text)
        write_text(cdir / "handoff.md", build_handoff(state))
        write_text(cdir / "bootstrap.md", build_bootstrap(state))
        event = {
            "at": utc_now(),
            "event": "checkpoint",
            "revision": revision,
            "workstream": state["workstream"],
            "redactions": redaction_count,
        }
        with (cdir / "events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        state["gates"]["hash_status"] = "passed"
        write_text(cdir / "current.yml", json.dumps(state, indent=2, ensure_ascii=False) + "\n")
        write_text(cdir / "handoff.md", build_handoff(state))
        write_text(cdir / "bootstrap.md", build_bootstrap(state))
        manifest = write_manifest(cdir, root, state)
        snap_dir = cdir / "snapshots" / timestamp()
        snap_dir.mkdir(parents=True, exist_ok=True)
        for name in list(HASHED_FILES) + ["manifest.json"]:
            path = cdir / name
            if path.exists():
                shutil.copy2(path, snap_dir / name)
        ok, errors, _ = validate_package_at(root, args.target)
        result = {
            "ok": ok,
            "continuity_dir": str(cdir),
            "revision": revision,
            "manifest": rel(cdir / "manifest.json", root),
            "snapshot": rel(snap_dir, root),
            "redactions": redaction_count,
            "errors": errors,
            "file_hashes": manifest["files"],
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if ok else 1
    finally:
        release_lock(lock)


def command_validate(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    ok, errors, state = validate_package_at(root, args.target)
    result = {
        "ok": ok,
        "continuity_dir": str(continuity_dir(root, args.target)),
        "revision": state.get("revision") if state else None,
        "gates": state.get("gates") if state else {},
        "errors": errors,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if ok else 1


def command_bootstrap(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    ok, errors, state = validate_package_at(root, args.target)
    if not ok or state is None:
        print(json.dumps({"ok": False, "errors": errors}, indent=2, ensure_ascii=False), file=sys.stderr)
        return 1
    if args.prepare_thread:
        if not args.approved_model.strip():
            print("Confirm creation and model choice first. Pass --approved-model MODEL after approval.", file=sys.stderr)
            return 2
        cdir = continuity_dir(root, args.target)
        lock = acquire_lock(cdir)
        try:
            request = write_rollover_request(
                root, args.target, args.thread_id or os.environ.get("CODEX_THREAD_ID", ""),
                {"reason": "requested_handoff"}, {}, {"ok": True}, args.approved_model.strip(),
            )
        finally:
            release_lock(lock)
        if request["status"] != "ready":
            print(json.dumps(request["validation"], ensure_ascii=False), file=sys.stderr)
            return 1
        text = request["prompt"]
    else:
        text = build_bootstrap(state)
    if args.output:
        output = Path(args.output).expanduser()
        write_text(output, text)
        print(json.dumps({"ok": True, "output": str(output.resolve())}, indent=2, ensure_ascii=False))
    else:
        print(text, end="")
    return 0


def command_redact(args: argparse.Namespace) -> int:
    if args.text is not None:
        raw = args.text
    elif args.file:
        raw = read_text(Path(args.file).expanduser())
    else:
        raw = sys.stdin.read()
    text, count = redact_text(raw)
    if args.output:
        write_text(Path(args.output).expanduser(), text)
    else:
        print(text, end="" if text.endswith("\n") else "\n")
    if args.report:
        print(json.dumps({"redactions": count}, indent=2), file=sys.stderr)
    return 0


def add_common_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", default=".", help="Workspace root. Default: current directory.")
    parser.add_argument("--target", default="", help="Optional target handoff name under .agent/continuity/targets/.")


def configure_checkpoint_parser(parser: argparse.ArgumentParser) -> None:
    add_common_root(parser)
    parser.add_argument("--workstream", default="")
    parser.add_argument("--latest-user-request", default="")
    parser.add_argument("--active-goal", default="")
    parser.add_argument("--goal-status", default="in_progress")
    parser.add_argument("--source", default="codex", help="Source of the checkpoint decisions, e.g. codex, claude, user, or sub-agent.")
    parser.add_argument("--evidence", default="")
    parser.add_argument("--decision", action="append")
    parser.add_argument("--open-task", action="append")
    parser.add_argument("--blocked-item", action="append")
    parser.add_argument("--changed-file", action="append")
    parser.add_argument("--context-file", action="append")
    parser.add_argument("--triparty-run-dir", default="")
    parser.add_argument("--force-lock", action="store_true")
    parser.set_defaults(func=command_checkpoint)


def configure_validate_parser(parser: argparse.ArgumentParser) -> None:
    add_common_root(parser)
    parser.set_defaults(func=command_validate)


def configure_bootstrap_parser(parser: argparse.ArgumentParser) -> None:
    add_common_root(parser)
    parser.add_argument("--output", default="")
    parser.add_argument("--prepare-thread", action="store_true", help="Prepare a thread request using the validated checkpoint as saved.")
    parser.add_argument("--approved-model", default="", help="Model ID selected for this new chat, including a concrete choice under an explicit delegation.")
    parser.add_argument("--thread-id", default="", help="Source thread for --prepare-thread. Defaults to CODEX_THREAD_ID.")
    parser.set_defaults(func=command_bootstrap)


def configure_redact_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--text")
    parser.add_argument("--file")
    parser.add_argument("--output")
    parser.add_argument("--report", action="store_true")
    parser.set_defaults(func=command_redact)


def configure_guard_parser(parser: argparse.ArgumentParser) -> None:
    add_common_root(parser)
    parser.add_argument("--thread-id", default="", help="Codex thread id. Defaults to CODEX_THREAD_ID.")
    parser.add_argument("--session-log", default="", help="Explicit rollout jsonl path. Defaults to lookup by thread id.")
    parser.add_argument("--workstream", default="")
    parser.add_argument("--latest-user-request", default="")
    parser.add_argument("--active-goal", default="")
    parser.add_argument("--next-task", default="")
    parser.add_argument("--source", default="codex", help="Source of the checkpoint decisions.")
    parser.add_argument("--decision", action="append")
    parser.add_argument("--open-task", action="append")
    parser.add_argument("--blocked-item", action="append")
    parser.add_argument("--warn-threshold", type=float, default=0.55)
    parser.add_argument("--checkpoint-threshold", type=float, default=0.70)
    parser.add_argument("--rollover-threshold", type=float, default=0.82)
    parser.add_argument("--bytes-checkpoint", type=int, default=25 * 1024 * 1024)
    parser.add_argument("--bytes-rollover", type=int, default=45 * 1024 * 1024)
    parser.add_argument("--large-output-chars", type=int, default=20000)
    parser.add_argument("--large-output-checkpoint-count", type=int, default=3)
    parser.add_argument("--large-output-rollover-count", type=int, default=6)
    parser.add_argument("--large-read-count", type=int, default=0)
    parser.add_argument("--large-read-checkpoint-count", type=int, default=4)
    parser.add_argument("--large-read-rollover-count", type=int, default=8)
    parser.add_argument("--artifact-count", type=int, default=0)
    parser.add_argument("--artifact-checkpoint-count", type=int, default=5)
    parser.add_argument("--phase-boundary", action="store_true")
    parser.add_argument("--major-evidence", action="store_true")
    parser.add_argument("--before-long-loop", action="store_true")
    parser.add_argument("--checkpoint", action="store_true", help="Write a checkpoint when severity reaches checkpoint_recommended.")
    parser.add_argument("--force-checkpoint", action="store_true")
    parser.add_argument("--force-rollover", action="store_true")
    parser.add_argument("--write-request", action="store_true", help="Write rollover-request.json after checkpoint validation.")
    parser.set_defaults(func=command_guard)


def configure_thread_receipt_parser(parser: argparse.ArgumentParser) -> None:
    add_common_root(parser)
    parser.add_argument("--created-thread-id", default="")
    parser.add_argument("--pending-worktree-id", default="")
    parser.add_argument("--thread-url", default="")
    parser.add_argument("--source-thread-id", default="")
    parser.add_argument("--tool", default="create_thread", choices=["create_thread", "fork_thread", "manual"])
    parser.add_argument("--target-type", default="projectless", choices=["project", "projectless", "same-directory", "worktree", "manual"])
    parser.add_argument("--note", default="")
    parser.set_defaults(func=command_thread_receipt)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Codex session continuity state.")
    sub = parser.add_subparsers(dest="command", required=True)

    checkpoint = sub.add_parser("checkpoint", help="Write a continuity checkpoint.")
    configure_checkpoint_parser(checkpoint)

    validate = sub.add_parser("validate", help="Validate continuity state.")
    configure_validate_parser(validate)

    bootstrap = sub.add_parser("bootstrap", help="Print or write resume bootstrap text.")
    configure_bootstrap_parser(bootstrap)

    redact = sub.add_parser("redact", help="Redact sensitive text.")
    configure_redact_parser(redact)

    guard = sub.add_parser("guard", help="Evaluate context pressure and optionally checkpoint or request rollover.")
    configure_guard_parser(guard)

    receipt = sub.add_parser("thread-receipt", help="Record a Codex thread creation receipt after create_thread or fork_thread succeeds.")
    configure_thread_receipt_parser(receipt)

    return parser


def build_wrapper_parser(command: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"{command}.py",
        description=f"Session continuity {command} command.",
    )
    if command == "checkpoint":
        configure_checkpoint_parser(parser)
    elif command == "validate":
        configure_validate_parser(parser)
    elif command == "bootstrap":
        configure_bootstrap_parser(parser)
    elif command == "redact":
        configure_redact_parser(parser)
    elif command == "guard":
        configure_guard_parser(parser)
    elif command == "thread-receipt":
        configure_thread_receipt_parser(parser)
    else:
        raise ValueError(f"Unknown wrapper command: {command}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


def main_default(command: str, argv: list[str] | None = None) -> int:
    args_list = list(argv or [])
    if args_list and args_list[0] == command:
        args_list = args_list[1:]
    parser = build_wrapper_parser(command)
    args = parser.parse_args(args_list)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
