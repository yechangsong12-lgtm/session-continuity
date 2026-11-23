# Session Continuity

English · [简体中文](README.zh-CN.md) · [Download the skill (.zip)](https://github.com/yechangsong12-lgtm/session-continuity/releases/latest/download/session-continuity.zip)

Pick up a long-running AI task in another chat or assistant. Session Continuity records what the user asked for, which decisions were made, where the evidence lives, and what to do next. With access to the workspace, the receiving assistant can verify the saved revision and check its first task against the original source.

For example, you might reconcile two supplier quotes in WorkBuddy and review the discrepancy in Claude Desktop. The handoff can point to the exact rows, explain which price still needs confirmation, and carry the question into the next chat. You can also finish the work where you started: a small correction or “continue” stays in the current chat.

## Choose your assistant

| Assistant | Set it up | Context and handoff |
| --- | --- | --- |
| Codex | Copy the skill to `~/.agents/skills/` or your project's `.agents/skills/`. [Codex skills](https://developers.openai.com/codex/skills) | The optional local hook detects 80% usage. You can opt in to a checkpoint; moving the whole task still requires your confirmation. [Hook setup](skills/session-continuity/references/context-settings.en.md) |
| DeepSeek Harness (DSH) | Install under `$DSH_HOME/skills/` or a Git project's `.dsh/skills/`. [DSH guide](skills/session-continuity/references/deepseek-harness.md) | Load `/session-continuity` in the workspace. Use DSH's own session data to check context pressure. |
| Tencent WorkBuddy | Import the ZIP in the Skills panel, or use the project's `.codebuddy/skills/`. [WorkBuddy guide](skills/session-continuity/references/workbuddy.md) | Check the task's context ring and selected model. Save the handoff in a workspace the next task can open. |
| Claude Desktop | Upload the ZIP for Chat or Cowork. The local Code tab can use Claude Code's skill directory. [Desktop setup by mode](skills/session-continuity/references/claude-desktop.md) | Share a summary and relevant files in Chat, use a connected folder in Cowork, or check the current context in the Code tab. |
| Claude Code CLI | Copy the skill to `~/.claude/skills/` or the project's `.claude/skills/`. [Claude Code skills](https://code.claude.com/docs/en/skills) | Call `/session-continuity`. An optional status line shows when usage reaches 80%. [Status line setup](skills/session-continuity/references/context-settings.en.md) |

For a directory installation, copy the entire `skills/session-continuity/` folder, including its license, so the installed entry is `session-continuity/SKILL.md`. The scripts use Python 3.11+ and its standard library. The upload-ready ZIP contains the same skill.

## Try a handoff

1. **Save.** Ask your assistant: “Prepare a handoff. Include the files you checked, the unresolved decisions and the first action for the next chat.” In a local workspace, checkpoints live under `.agent/continuity/`.
2. **Choose where to continue.** Routine work stays in the main chat. When the host supports background subagents, they can handle bounded research or data cleanup and return findings, sources and detail files. Before opening a visible side chat, confirm the purpose and model. For a full transfer at 80%, the skill offers to keep the source model.
3. **Resume.** In the receiving chat, open the workspace and ask: “Verify the handoff, check the evidence for the first open item and continue.” If the two assistants see different filesystem paths, export a portable brief from the source skill directory:

   ```sh
   python scripts/bootstrap.py --root "/path/to/work" --portable --output handoff.md
   ```

   Give the receiver that brief and access to the evidence it needs. A text-only receiver reports what it could actually inspect. File integrity checks cover the saved checkpoint; important figures still need to be checked against the source.

A side chat returns its work to the main chat. Cleanup applies to the side chat once both tasks finish and its evidence is retained. Archiving the source after a full transfer requires confirmed takeover and your agreement. [Full workflow](skills/session-continuity/SKILL.md)

## Origin and license

Session Continuity extends the checkpoint, validation, bootstrap and receipt tools from [r-design-j/codex-session-continuity-skill](https://github.com/r-design-j/codex-session-continuity-skill). This edition maintains the bilingual workflow, client integrations, context alerts and model confirmation. Both the repository and the installable skill carry the original copyright notice. [MIT license](LICENSE)
