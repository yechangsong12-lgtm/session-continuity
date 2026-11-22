# Session Continuity

English · [简体中文](README.zh-CN.md)

Session Continuity is an English and Simplified Chinese agent skill for long-running work in Codex and Claude Code. Delegate bulk work to an economical subagent, keep a record of decisions and evidence, and let a new chat pick up from a verified checkpoint.

## Install

Copy the `skills/session-continuity` directory to one of the locations below. The bundled scripts require Python 3.11 or later. The Markdown handoff format also works in environments without local script execution.

| Client | Personal installation | Project installation |
| --- | --- | --- |
| Codex | `~/.agents/skills/session-continuity/` | `.agents/skills/session-continuity/` |
| Claude Code | `~/.claude/skills/session-continuity/` | `.claude/skills/session-continuity/` |

The installation directory should contain `SKILL.md` directly. See [Codex skill installation](https://developers.openai.com/codex/skills) and [Claude Code skills](https://code.claude.com/docs/en/skills).

## Use it

- **Delegate research or data cleanup.** Ask “Reconcile these two price lists” or “Look up the specifications for these five products.” Codex can select the skill from the request. Choose a model for this task, set a fixed preference, or let the agent pick a capable low-cost model. The result includes key findings, sources and the location of detailed files.
- **Choose a separate chat.** Continue edits to the same deliverable, including a single-image fix, in its current chat. For a side task that needs independent follow-up, the assistant asks whether to open a separate chat and which model to use. Bring the side task’s findings and evidence back to the main chat. Once both tasks finish and the side chat has no pending work, review, unique evidence or retention request, it can be archived with automatic-cleanup permission. Otherwise ask about that specific side chat when eligible. The main chat stays active.
- **Hand off at 80%.** Register the Codex hook for a visible reminder. Enable `auto_checkpoint_at_80` to checkpoint automatically. Before opening a visible successor, the assistant asks whether to open it and which model to use unless the user has already made both choices for this transfer or as a standing preference. After the whole main task moves and the successor confirms its revision and next step, the source rechecks usage and remaining work. Ask about archiving the source only if it still meets 80% and has no remaining work. After compaction releases space, keep it active. Claude Code users can add an 80% reminder to their status line. [Context settings and adapters](skills/session-continuity/references/context-settings.en.md)
- **Resume work.** Ask “Prepare a handoff for this project.” In the next chat, say “Validate the checkpoint in the same workspace and continue from the first open task.” To invoke the skill explicitly, use `$session-continuity` in Codex or `/session-continuity` in Claude Code. Ask in Chinese or English and the assistant follows that language.

The default checkpoint location is `.agent/continuity/` inside the workspace. [Full workflow](skills/session-continuity/SKILL.md)

## License

[MIT](LICENSE)
