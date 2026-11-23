---
name: session-continuity
description: Keep work in the current chat, delegate bounded research, or hand off to a new chat in the same assistant. 同一助手内的任务分工、80% 存档、跨对话接续和归档。Optional Codex 1M setup.
---

# Session Continuity

English · [简体中文](references/workflow.zh-CN.md)

Keep the user's task in its current chat by default. Use a new visible chat in the **same assistant** when there is a specific reason below. Carry forward all compatible requests and use the user's language.

## Choose where the work goes

| What is happening? | What to do |
| --- | --- |
| The user says “continue”, requests a correction, or is still refining the same deliverable. | Work here. Fixing the teeth in one product image belongs with the rest of that image set. |
| A bounded search or batch job can return one result for the main task. | Use a background subagent if available. Bring back key findings, sources and the location of any detailed file. The main chat stays active. |
| There is a separate deliverable that needs the user's own follow-up across multiple rounds, and the main task can proceed independently. | Propose a side chat. For example, one supplier's conflicting quote needs a reply and a later purchasing decision while the catalog work continues. Explain the part that would move and ask whether to open the chat and which model to use. |
| The user expressly asks for a new chat, or the **whole unfinished task** still needs to move after a high-context checkpoint. | Honor the requested scope. Confirm any outstanding creation or model choice, then use the handoff steps below. |

**Model choice.** For a new model choice, offer the models actually available to that account for that kind of task. The user can name one or let the agent choose. Apply an existing preference that covers this task. When delegated the choice, use a capable, economical model and say which one. If the user has already authorized a specific chat, ask only for the missing selection.

## Checkpoint and resume

1. At **80% of the current chat's effective window**, follow the user's reminder or automatic checkpoint setting. Check the latest reading again after compaction. Keep working here if there is room or only a small change remains. If no reliable reading exists, offer a checkpoint at a work boundary.
2. Save the current goal, corrections, decisions and reasons, checked files or sources, pending work and one concrete next action. Keep credentials and access-bearing URLs out. For local work use the same workspace and optional `--target` for each command:

   ```text
   python scripts/checkpoint.py --root WORKSPACE --active-goal "Reconcile supplier quotes" --context-file quotes.csv --open-task "Check the currency in row 31"
   python scripts/validate.py --root WORKSPACE
   python scripts/bootstrap.py --root WORKSPACE
   ```

   Read `.agent/continuity/handoff.md` for the summary. If the chat only accepts text, give the user a concise handoff they can paste into a **new chat in this assistant** with the evidence it needs. Distinguish a file-verified revision from a summary reviewed in chat.
3. For a full transfer at 80%, name the current model and offer to keep it if available. Ask “Open the next chat with this model, choose another, or stay here?” Wait for the user's choice. Recheck usage and model before creating anything. Reuse the existing destination if an earlier attempt already created it.
4. In the new chat, validate the expected revision when files are available, inspect an original source for the first open task and report the next action. The main chat checks that acknowledgement. A newly created chat alone does not establish takeover.

## Close the right chat

A side chat returns its results to the main chat. Consider archiving the **side chat** when both tasks are done, its evidence is accessible from the main chat and nothing needs review or retention. Archive it automatically only under the user's cleanup preference; otherwise ask about that specific chat.

For a full transfer, recheck the source chat's usage and remaining work. Ask about archiving the **source chat** only after the entire task has moved, the new chat confirmed takeover, the source still meets the threshold and has no remaining work. Archive that source only with explicit consent.

## Setup and commands

- **Codex.** On an explicit 1M request, verify model support and run `python scripts/context_window.py --set 1000000`. Read back the setting, then check a fresh session's effective window. [1M, the 80% hook and transfer commands](references/context-settings.en.md)
- **Other supported assistants.** Use the installation path, model selector and usage reading for the assistant where the task started. [DeepSeek Harness](references/deepseek-harness.md) · [WorkBuddy](references/workbuddy.md) · [Claude Desktop](references/claude-desktop.md) · [Claude Code CLI status line](references/context-settings.en.md#configure-the-claude-code-status-line)
- **Troubleshooting.** [Checkpoint format](references/schema.md) · [Recovery](references/failure-modes.md)

The checkpoint tools are adapted from [r-design-j/codex-session-continuity-skill](https://github.com/r-design-j/codex-session-continuity-skill). [MIT license and copyright notices](LICENSE)
