# Session Continuity Schema

`current.yml` is JSON-compatible YAML. Scripts write JSON to keep parsing deterministic without PyYAML.

Required top-level fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `schema` | string | Must be `codex-session-continuity/v1`. |
| `revision` | integer | Monotonic version. Increment on each checkpoint. |
| `created_at` | string | First checkpoint timestamp in UTC. |
| `updated_at` | string | Latest checkpoint timestamp in UTC. |
| `workspace_root` | string | Absolute root path used when generating the checkpoint. |
| `workstream` | string | Stable name for the task family. |
| `latest_user_request` | string | Latest user-visible request being carried forward. |
| `active_goal.status` | string | `in_progress`, `complete`, `blocked`, or a local status. |
| `active_goal.objective` | string | Concrete objective to resume. |
| `decisions[]` | array | Durable decisions with `text`, `source`, and optional `evidence`. |
| `open_tasks[]` | array | Next actions. |
| `blocked_items[]` | array | Blockers that require user input or external change. |
| `changed_files[]` | array | Workspace files known to be changed. |
| `context_to_load[]` | array | Files a new session should read first. |
| `gates` | object | Resume safety gates. |
| `triparty` | object | Optional Codex + Claude + Gemini run evidence. |

Gate values:

- `probe_status`: `passed` or `failed`
- `review_status`: `passed`, `partial`, or `not_required`
- `redaction_status`: `passed` or `failed`
- `hash_status`: `passed` or `failed`
- `bootstrap_status`: `ready` or `blocked`

`manifest.json` records SHA256 hashes for:

- `current.yml`
- `handoff.md`
- `bootstrap.md`
- `events.jsonl`

Validation must fail on hash mismatch, unreadable JSON, missing manifest, missing current state, or suspected secrets.

For tri-party workstreams, `review_status: passed` requires:

- `claude-review.md` exists, is non-empty, and contains `TRIPARTY_REVIEW_COMPLETE`.
- `gemini-review.md` exists, is non-empty, and contains `TRIPARTY_REVIEW_COMPLETE`.
- `claude-cross-audit.md` and `gemini-cross-audit.md` both contain `TRIPARTY_CROSS_AUDIT_COMPLETE`.
- `state.json` has `true_triparty_ready: true`, or `merge-status.md` has `Ready for true tri-party synthesis`.
- Artifact metadata includes the expected `party` and `stage` labels.
- When `state.json` records artifact SHA256 values, those values match the current files on disk.

Validation blocks resume while another live process owns `.agent/continuity/locks/writer.lock`. A fresh lock with incomplete owner information is also treated as active.

## Context Guard Output

`guard.py` prints a JSON object. It does not mutate files unless `--checkpoint`,
`--force-checkpoint`, or `--write-request` is supplied.

Important fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `metrics.session_log` | string | Rollout log used as the evidence source. |
| `metrics.latest_context_ratio` | number/null | Latest input token count divided by model context window when available. |
| `metrics.compaction_markers` | integer | Count of explicit compaction markers seen in structured log events. |
| `metrics.large_tool_outputs` | integer | Tool outputs above the configured large-output threshold. |
| `evaluation.severity` | string | `ok`, `watch`, `checkpoint_recommended`, or `rollover_required`. |
| `evaluation.action` | string | `none`, `checkpoint`, or `review_in_current_chat`. |
| `evaluation.reasons[]` | array | Trigger reasons used for the decision. |
| `checkpoint` | object/null | Checkpoint command result when a checkpoint was written. |
| `rollover_request` | object/null | Summary of generated `rollover-request.json`. |

## Rollover Request

`rollover-request.json` is generated under the same continuity directory as the
current handoff. It is a request to create or fork a fresh Codex thread. It is
not proof that a thread was created.

Required fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `schema` | string | Must be `codex-session-continuity/rollover-request/v1`. |
| `generated_at` | string | UTC request timestamp. |
| `workspace_root` | string | Workspace root used for checkpoint and validation. |
| `source_thread_id` | string | Current Codex thread id when available. |
| `continuity_dir` | string | Directory containing `current.yml`, `handoff.md`, and `bootstrap.md`. |
| `bootstrap_path` | string | Bootstrap file to send to the next thread. |
| `prompt` | string | Initial prompt for the fresh Codex thread. |
| `prompt_sha256` | string | SHA256 of `prompt`. |
| `status` | string | `ready` or `blocked`. |
| `thread_action` | string | `confirm_chat_and_model` while a choice is outstanding, `create_thread` after approval, or `manual_repair_required`. |
| `approved_model` | string | Concrete model selected for this transfer after authorization. |
| `validation` | object | Validation gates and errors at request time. |
| `trigger` | object | Context-pressure evaluation. |
| `metrics` | object | Session-log metrics used by the guard. |
| `checkpoint` | object | Checkpoint command result. |

For a confirmed 80% transfer, compare the saved model with the model named in the confirmation, and pass that exact ID to the chat creation tool.

If `status` is not `ready`, no new thread should be created from the request.

## Thread Receipt

`thread-receipt.json` records the result after the Codex App thread tool runs.
Only this receipt can upgrade a ready rollover request into a completed thread
action. A `created` or `pending_worktree` receipt requires the request status,
continuity revision, target, workspace root, and bootstrap prompt hash to match
the current continuity package.

Required fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `schema` | string | Must be `codex-session-continuity/thread-receipt/v1`. |
| `recorded_at` | string | UTC receipt timestamp. |
| `source_thread_id` | string | Thread that requested the rollover. |
| `created_thread_id` | string | New Codex thread id, if one was created. |
| `pending_worktree_id` | string | Pending worktree id, if worktree setup is still queued. |
| `status` | string | `created`, `pending_worktree`, or `manual_required`. |
| `continuity_revision` | integer | Revision used to bootstrap the new thread. |
| `continuity_gates` | object | Gates at receipt time. |
| `bootstrap_sha256` | string | SHA256 of the bootstrap prompt at receipt time. |
| `rollover_request_sha256` | string | SHA256 of `rollover-request.json` when present. |

Do not claim a rollover is complete when `status` is `manual_required`.
