# Failure Modes

Hard-stop failures:

- `hash_status: failed`: a continuity file changed after manifest generation.
- `redaction_status: failed`: likely secret material is present.
- Missing `current.yml` or invalid JSON-compatible YAML.
- Missing `manifest.json`.
- Active `locks/writer.lock` younger than 15 minutes.
- A tri-party workstream claims complete review without Claude and Gemini evidence files.
- Tri-party evidence files are empty, lack completion markers, or lack `true_triparty_ready` / merge-gate readiness.
- Tri-party artifact metadata does not match the expected party/stage.
- Tri-party `state.json` hashes do not match current artifact files.
- Credential-bearing URLs such as database DSNs appear in continuity state.

Soft failures:

- `review_status: partial`: resume is allowed, but label the result as partial.
- Empty `open_tasks`: ask the user or inspect recent project files before acting.
- Missing `changed_files`: inspect `git status` if the workspace is a git repository.

Recovery steps:

1. From the installed skill directory, run `python3 scripts/validate.py --root "/path/to/work"` with the original target if applicable.
2. If hashes fail, inspect whether files were manually edited after checkpoint.
3. If redaction fails, remove secrets and re-run checkpoint.
4. If the lock is stale, rerun checkpoint with `--force-lock`.
5. If tri-party evidence is partial, run or resume the tri-party framework before calling the result complete.
