# Tri-party Continuity Rules

Use this reference when a workstream involves the Codex + Claude + Gemini tri-party framework.

Roles:

- Codex: implementation owner and final synthesis owner.
- Claude: reasoning, autonomy, and architecture reviewer.
- Gemini: external context, multimodal, and failure-mode reviewer.

Continuity must preserve source labels:

- Do not summarize Claude or Gemini as if Codex produced the same opinion.
- Keep review artifacts as evidence paths.
- Use `review_status: partial` when one model review or cross-audit is missing.
- Use `review_status: passed` only when Claude review, Gemini review, and cross-audit artifacts exist.

Expected run directory evidence:

- `claude-review.md`
- `gemini-review.md`
- `claude-cross-audit.md`
- `gemini-cross-audit.md`
- `state.json` when available

Passing continuity review status requires completed artifacts, not just file existence. Review files must include `TRIPARTY_REVIEW_COMPLETE`; cross-audit files must include `TRIPARTY_CROSS_AUDIT_COMPLETE`; artifact metadata must preserve expected party/stage labels; `state.json` or `merge-status.md` must indicate true tri-party readiness. When `state.json` records artifact hashes, compare those hashes to disk before marking the run as `passed`.

Probe and review are separate:

- `probe_status` means files and tools were reachable.
- `review_status` means the actual model review lifecycle completed.

Never claim `Ready for true tri-party synthesis` from continuity state alone. The merge gate output from the tri-party framework remains authoritative.
