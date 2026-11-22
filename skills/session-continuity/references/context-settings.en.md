# Context settings and the 80% handoff

English · [简体中文](context-settings.md) · [Session workflow](../SKILL.md)

## Read or set the Codex context window

Use Python 3.11+ from the installed skill directory. On Windows, substitute your Python executable or `py -3`. Use the last command only after the user chooses a new value supported by their model.

```text
python3 scripts/context_window.py
python3 scripts/context_window.py --config /path/to/test-config.toml
python3 scripts/context_window.py --set <requested-positive-integer>
```

The default is `$CODEX_HOME/config.toml`, falling back to `~/.codex/config.toml`. Reading prints only the root-level `model_context_window` or `unset`. Updates preserve unrelated settings, profiles, comments and line endings. After an update, reread the value and verify the effective window in a chat that has loaded the new configuration. Use `/status` when available. For an exact local log value, read `info.model_context_window` from the relevant chat's most recent usable `token_count`.

`model_auto_compact_token_limit` controls normal automatic compaction. An unset value uses the model default. `model_post_turn_compact_threshold_percent` controls compaction after a completed turn. The hook below makes its own 80% measurement. [Codex configuration](https://learn.chatgpt.com/docs/config-file/config-reference) · [Models and context](https://learn.chatgpt.com/docs/models) · [Desktop slash commands](https://learn.chatgpt.com/docs/reference/slash-commands)

## Register the Codex hook

1. Inspect the skill's `scripts/context-reminder.py` and copy it to `$CODEX_HOME/hooks/context-reminder.py`. The default Codex home is `~/.codex`. On Windows, discover your interpreter with `py -3 -c "import sys; print(sys.executable)"`. On macOS or Linux, use `command -v python3`.
2. In the user's `$CODEX_HOME/hooks.json`, append a command group to each required event. Replace the example interpreter and script paths with absolute paths on the target machine. Keep existing event groups and other fields. If this configuration layer already uses `config.toml` for hooks, extend its existing tables using the official format. Register the reminder only once for each event.
3. Reload the client and review the hook in `/hooks` or the desktop Hooks settings. Check the command and trust the definition you reviewed. Trust is bound to the hook definition. After a definition changes, review any new trust prompt. [Codex hooks and trust](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks)

For a new `hooks.json`, configure the four events shown below. The example uses POSIX paths. On Windows, replace each command with the corresponding Windows paths, such as `"C:/Path To Python/python.exe" -B -X utf8 "C:/Path To Codex/hooks/context-reminder.py"`. Preserve JSON escaping inside string values.

```json
{
  "hooks": {
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "\"/path/to/python3\" -B -X utf8 \"/path/to/codex/hooks/context-reminder.py\"", "timeout": 5}]}],
    "PostToolUse": [{"hooks": [{"type": "command", "command": "\"/path/to/python3\" -B -X utf8 \"/path/to/codex/hooks/context-reminder.py\"", "timeout": 5}]}],
    "Stop": [{"hooks": [{"type": "command", "command": "\"/path/to/python3\" -B -X utf8 \"/path/to/codex/hooks/context-reminder.py\"", "timeout": 5}]}],
    "PreCompact": [{"matcher": "^auto$", "hooks": [{"type": "command", "command": "\"/path/to/python3\" -B -X utf8 \"/path/to/codex/hooks/context-reminder.py\"", "timeout": 5}]}]
  }
}
```

To deliver a deferred crossing immediately after compaction on clients supporting it, add the same command under `SessionStart` with matcher `^compact$`. The next supported event can also deliver it. For a safe command smoke test, send `{}` to the script on stdin. It should exit successfully with no output. [Hook event reference](https://learn.chatgpt.com/docs/hooks)

## Reminder or automatic handoff

By default, the hook shows a reminder. To checkpoint automatically, set this preference in `$CODEX_HOME/hooks/session-continuity.json`. Set it to `false` to return to reminders. The earlier `auto_handoff_at_80` key is supported when `auto_checkpoint_at_80` is absent. Both settings authorize automatic checkpointing. Enabling automatic checkpoints and authorizing visible chat creation are separate choices.

```json
{"auto_checkpoint_at_80": true}
```

The measured ratio is the source chat's latest usable `info.last_token_usage.total_tokens` divided by its `info.model_context_window`. It can differ from the client meter. The hook checks the chat ID and local transcript and suppresses repeat notifications for the same crossing. When an event is deferred across compaction, the earlier, qualifying sample belongs to that same chat. During diagnosis, verify the original sample, numerator and denominator. Keep deliberately simulated test readings identified as such.

`UserPromptSubmit` and `PostToolUse` can send the instruction to the assistant. `Stop` can request one follow-up turn. `PreCompact` can defer delivery until a supported event. After compaction, recheck current usage and retain the source when enough space has returned. Save the validated checkpoint automatically. For a full migration, look up the actual model with `bootstrap.py --show-source-model --thread-id UUID`. Ask “Open a successor chat using the current model, X? You can choose another model.” Wait for this transfer’s explicit consent. Prepare the request with `--prepare-thread --inherit-source-model --expected-source-model MODEL_SHOWN --thread-id UUID`, adding `--approved-model OVERRIDE` when the user picks a different model. Pass the resulting `approved_model` explicitly to the host and verify the actual destination model. Keep the source active and ask if the selected model is missing, unavailable or unverified. Before asking whether to archive the source of a full migration, remeasure actual usage, check that no work remains there, and verify the successor’s acknowledgement. If compaction has dropped usage or the source still holds work, keep it open. The full-migration archive question applies only to a source still at or above 80%, or to a chat the user explicitly asks to archive. Routine side tasks leave the main chat active. If both tasks are complete and side-chat evidence is consolidated, review that specific side chat for cleanup under the [workflow](../SKILL.md). An authorized simulation may ask about the temporary test source only. Where the host cannot create or observe a successor, keep the source open and provide the checkpoint and startup prompt. If a hook lacks a reliable usage sample, use the client meter or a checkpoint at a work boundary. [Handoff steps](../SKILL.md) Replace MODEL_SHOWN with the exact source model ID from the confirmation prompt. If it has changed, preparation stops for fresh consent.

The assistant follows the source conversation's language. For short host notices without access to the conversation, the hook uses the process locale. Chinese locales use Chinese and other locales use English. The preference order is `LC_ALL`, `LC_MESSAGES`, `LANGUAGE`, `LANG`, then the system locale.

## Configure the Claude Code status line

The adapter reads Claude Code's native `context_window.used_percentage` from the JSON supplied on stdin. It shows a handoff reminder at 80% and above. The reminder disappears when the value falls. Missing, null or invalid readings produce no output. The status line displays the reminder. To continue in another chat, request a handoff from the current session and validate the result in the receiving one. [Claude Code status line](https://code.claude.com/docs/en/statusline#context-window-fields)

Add the `statusLine` field to `~/.claude/settings.json` or the project's `.claude/settings.json`. Use the adapter's actual absolute path. Preserve other settings and any existing status-line features. The optional `--lang en` selects English, `--lang zh` selects Chinese, and `--lang auto` follows the locale.

```json
{
  "statusLine": {
    "type": "command",
    "command": "\"/absolute/path/to/python3\" -B -X utf8 \"/absolute/path/to/claude_context_status.py\" --lang en"
  }
}
```

When a status line already exists, read its JSON input once and pass the same data to both commands. The adapter's `--reminder-only` mode returns text only at or above 80%. Configure the host to execute your wrapper script and substitute your actual paths. [Manual status-line setup](https://code.claude.com/docs/en/statusline#manually-configure-a-status-line)

```bash
#!/usr/bin/env bash
input=$(cat)
base=$(printf '%s' "$input" | "/path/to/existing-statusline")
reminder=$(printf '%s' "$input" | "/path/to/python3" -B -X utf8 "/path/to/claude_context_status.py" --reminder-only --lang en)
[ -z "$reminder" ] || base="${base:+$base | }$reminder"
printf '%s\n' "$base"
```

```powershell
$payload = $input | Out-String
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$base = ($payload | & 'C:/path/to/existing-statusline.ps1' 6>&1) -join "`n"
$reminder = $payload | & 'C:/path/to/python.exe' -B -X utf8 'C:/path/to/claude_context_status.py' --reminder-only --lang en
if ($base -and $reminder) { "$base | $reminder" } elseif ($reminder) { $reminder } else { $base }
```

Test with `{"context_window":{"used_percentage":80}}`, then `79` and `null`. In reminder-only mode, only the first input should print a message. When custom status lines are unavailable, use Claude Code's `/context` command. [Windows configuration](https://code.claude.com/docs/en/statusline#windows-configuration) · [Claude Code commands](https://code.claude.com/docs/en/commands)
