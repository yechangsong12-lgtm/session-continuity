# Session Continuity

English · [简体中文](README.zh-CN.md) · [Download the skill (.zip)](https://github.com/yechangsong12-lgtm/session-continuity/releases/latest/download/session-continuity.zip)

Save progress on a long task and pick it up in a new chat **within the same assistant**. The checkpoint records what the user asked for, what changed, where to find the evidence and the first unfinished step. The new chat checks that record before continuing.

## When should a new chat open?

| Your task | What the skill does |
| --- | --- |
| The goal is the same and the user is continuing the work, adding requirements, or revising or checking an existing result. | Continue in the current chat with its context and decisions. |
| Part of the work can be completed independently and the main task only needs its result. | Use a background subagent if available. Return the findings, sources and location of any detailed results to the main chat. |
| A side task has its own outcome, needs ongoing user follow-up, and can proceed alongside the main task. | Suggest a separate chat. Explain what would move and why, then confirm whether to open it and which model to use. |
| Context usage reaches 80% while the main task is still unfinished. | Checkpoint according to the user’s settings and recheck current usage. Continue here if there is room. Ask before moving the whole task to a new chat. |

You can also request a new chat directly. For a model choice, select an available model yourself or let the agent choose. Existing preferences for the same kind of task carry forward. For a full migration the skill offers to keep the current model when available.

A side chat returns its result to the main chat. Consider cleaning up the **side chat** after both tasks finish and all evidence is retained. Archiving the **original chat** after a full migration requires verified takeover and your explicit agreement.

## Why consider 1M context in Codex?

Project instructions, Markdown files the assistant actually reads, and past decisions can consume tens of thousands of tokens before a large project’s first edit. In a November 2026 Codex desktop model catalog, GPT‑6.2 Sol’s 500K default and Astra’s 272K default gave effective windows of **475K and 258.4K** at a 95% allowance. With 60K already used for project material, Astra would have **198.4K** left for the conversation, code and tool results.

A compressed summary may remember “we chose B” and omit why A was rejected. A larger window gives the assistant more room to compare the original requirements and evidence. On supported Codex models you can ask this skill to set **1,000,000 tokens** and report the effective window in a fresh session. The 95% allowance in the example and the threshold for automatic compaction are separate settings. The skill’s optional checkpoint uses **80% of the observed effective window**. [Official model limits](https://learn.chatgpt.com/docs/models?surface=app) · [Compaction settings](https://learn.chatgpt.com/docs/config-file/config-reference) · [1M setup](skills/session-continuity/references/context-settings.en.md#codex-1m)

## Install and try it

Install in the assistant you already use. Each guide covers that client's skill folder or ZIP import and its available context readings.

| Client | Where to start |
| --- | --- |
| Codex | Copy the complete skill folder to `~/.agents/skills/` or the project's `.agents/skills/`. [Optional 80% hook](skills/session-continuity/references/context-settings.en.md) |
| DeepSeek Harness | Use `$DSH_HOME/skills/` or the project's `.dsh/skills/`. [DSH guide](skills/session-continuity/references/deepseek-harness.md) |
| Tencent WorkBuddy | Import the release ZIP in the Skills panel, or use the project's `.codebuddy/skills/`. [WorkBuddy guide](skills/session-continuity/references/workbuddy.md) |
| Claude Desktop | Choose the instructions for Chat, Cowork or the Code tab. [Desktop guide](skills/session-continuity/references/claude-desktop.md) |
| Claude Code CLI | Copy the skill to `~/.claude/skills/` or the project's `.claude/skills/`. [Optional status line](skills/session-continuity/references/context-settings.en.md#configure-the-claude-code-status-line) |

Ask **“Save a checkpoint with the evidence and the first unfinished step.”** After you choose to move, ask the new chat in the same assistant to validate that checkpoint and resume. Local scripts require Python 3.11+ and use `.agent/continuity/` in the workspace. In a text-only chat, paste the handoff and attach the evidence the next step requires. [Full workflow](skills/session-continuity/SKILL.md)

## Origin and license

This project extends the checkpoint, validation and receipt tools in [r-design-j/codex-session-continuity-skill](https://github.com/r-design-j/codex-session-continuity-skill). The repository and installable skill both include the upstream copyright notice and [MIT license](LICENSE).

To test a checkout, run `python skills/session-continuity/scripts/self_test.py` and `python -m unittest discover -s tests` from the repository root.
