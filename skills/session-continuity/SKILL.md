---
name: session-continuity
description: Delegate bulk data cleanup and simple web searches to low-cost subagents, monitor context usage, and checkpoint, hand off or resume chats at 80%. 批量整理、简单搜索、上下文设置、80% 自动存档、开聊及选型确认、续接和归档。
---

# Session Continuity

English · [简体中文](references/workflow.zh-CN.md)

Use the user's requested language for summaries, alerts you write, takeover acknowledgements and the archive question. When the user has not specified a language, follow the conversation. Pass that choice along with the work. Keep IDs, paths, source quotes and numerical evidence intact. Use side-by-side translations when requested. 中文任务可直接使用上方的简体中文指南。

## Decide where the work belongs

| Situation | Action |
| --- | --- |
| Bulk data cleanup, straightforward searches, long logs or clearly bounded checks | Delegate to a subagent with its own context. Specify scope, input locations, expected result and files it may change. |
| “Continue”, a small revision to the same deliverable, or fixing one image | Continue in the same chat. |
| Trying a second approach from the same discussion | Explain the alternative and ask whether to branch and which available model to use. Wait for consent. |
| A new goal, or a side task the user wants to monitor and direct independently | Ask whether to open a separate chat and which model to use. Offer the current model, a specific available model, or agent selection. Wait for consent. Keep the main chat active. |
| The source chat reaches 80% of its effective context window | Follow the user's reminder or automatic checkpoint preference below. |

Codex may select this skill from the task description. The delegation, branch and fresh-chat choices draw on Claude Code's guidance. The 80% threshold belongs to this skill. [Claude Code subagents](https://code.claude.com/docs/en/sub-agents) · [Sessions](https://code.claude.com/docs/en/sessions) · [Best practices](https://code.claude.com/docs/en/best-practices)

A background subagent returns its findings to the current chat. An ordinary side chat is a user-visible workspace the user can direct independently. When requesting consent for a side chat, clarify whether the model choice applies this time or should become a fixed or automatic preference. Once the side chat takes over its part, the main chat continues. A side task never prompts archiving the main chat. Bring the side chat’s results, sources and detailed file locations back to the main chat first. Once both tasks are complete, check for outstanding work or review, evidence held only in the side chat, and a request to keep it. Keep the side chat available while any of those remain. When it is eligible for cleanup, archive the named **side chat** automatically only if the user authorized automatic cleanup. Otherwise ask about that specific side chat.

## Delegate and bring back the findings

Honor a model selected for this task. Save a fixed choice only when the user asks for it within an identified scope. If the choice materially affects the work and the user has no established preference, offer three options: choose for this task, choose a standing model, or let the agent pick. For automatic selection, prefer a low-token-cost model that has the tools, context and accuracy the task requires. Use the host's economy tier when verified prices are unavailable. If the fixed model is unavailable, identify available substitutes before changing the standing preference.

Ask the subagent for **key findings, sources and the location of detailed results**. Include unresolved discrepancies and the source date, page, sheet or row when it matters. Reuse existing detail files. A short search can return its links directly. In the main chat, check the figures and samples that affect the decision. When the host lacks independent subagents or model selection, describe how the work was performed.

## What to do at 80%

For the Codex window setting, event hook and Claude Code status line, see [context settings in English](references/context-settings.en.md) or [简体中文](references/context-settings.md).

New installations show a reminder when the Codex hook is registered. A user can enable automatic checkpointing in their personal `$CODEX_HOME/hooks/session-continuity.json` with `{"auto_checkpoint_at_80": true}`. That choice lets the source save and validate its checkpoint automatically. For a full-task migration, read the actual source model and ask one question: “Open a successor chat using the current model, X? You can choose another model.” Accepting the proposed model covers model selection for this transfer. Create the chat only after the user explicitly agrees to open it this time. “Continue” keeps the work in this chat. An economy-model preference for background subagents is separate.

1. **Verify the crossing.** Use the host's effective window and an actual usage sample from the source chat. For a deferred event after compaction, verify the earlier qualifying sample in that same source chat and recheck its current usage. If compaction has restored ample room, keep the source chat active and reassess the need for transfer. Simulations use only their designated test chats. If usage is unavailable, offer a checkpoint at a work boundary and describe what prompted it.
2. **Checkpoint once.** Check existing requests and receipts for this source chat and transfer. Reuse a known successor or pending creation ID. Save and validate the current revision, including the workspace, active goal, outstanding requests and next action.
3. **Create the successor.** Use the validated startup prompt and original workspace. Supply the request’s verified `approved_model` explicitly to the host’s create action. Record the returned ID and verify the actual model in the successor. If the model is unavailable, unverified, or differs from what the user approved, keep the source open and ask how to proceed. If creation is uncertain, check the host and receipt before retrying. Keep one owner for the work while the source observes the handoff.
4. **Verify takeover.** In its own chat, the successor validates the expected revision, opens the handoff, checks the evidence for the first task, and states its next action or verified completion or blocker in the user's language. The source observes this real response through the host, for example with Codex `wait_threads`. Match the chat ID, revision and task. A pending ID or a receipt identifies the destination. Its reply establishes takeover.
5. **Ask about the source only for a full migration.** Immediately before asking, measure the actual source again and check for additional work left there. Keep it active if usage has fallen after compaction or work remains. Confirm the source still meets the 80% threshold, the entire main task moved and the successor acknowledged takeover. Then provide the destination and ask once, “The new chat has taken over. Would you like to archive this original chat?” Archive only the identified source after explicit agreement. Also honor a user’s explicit archive request for a named chat. A simulation may exercise the archive question only for its designated temporary source if the user requested that test. Side chats and handoff tests leave business chats active. If creation or verification remains pending, deliver the checkpoint and describe what remains.

Claude Code's status-line adapter displays usage and the threshold reminder. The user can request a handoff when the prompt appears. Other hosts can use their own context readings, model routing and chat controls.

## Write the checkpoint

- **Goal and constraints.** Name the deliverable, destination, acceptance criteria and authorized scope. Carry forward compatible requests added mid-task alongside the latest corrections. Mark decisions that still belong to the user.
- **Progress and decisions.** Separate completed and verified work, active jobs and remaining tasks. For important decisions, record who decided, the rationale and the evidence. Distinguish user approval from an inferred preference or a successful technical check.
- **Evidence and artifacts.** Include source links or paths, sheet names and rows, dates and verification results. Record running job IDs and the next safe check. Keep credentials, access-bearing URLs and full chat logs out of the checkpoint.
- **First next action.** Identify a concrete step, the file or system to use, and the expected result. Include relevant blockers or failed approaches. From a fresh chat, verify that the cited evidence can be found.

## Save, resume and record a destination

Run the scripts with Python 3.11+ from the installed skill directory. Pass the same `--root` and optional `--target` throughout. For independent goals in the same workspace, use distinct short ASCII target names and put the full user-facing labels in the summary. Read the current checkpoint before revising it. Keep active decisions, evidence, tasks and blockers in the next revision.

```text
python scripts/checkpoint.py --root "/path/to/work" --latest-user-request "Check quoted prices" --active-goal "Reconcile the price sheet" --decision "Rows 2 through 30 match the supplier file" --context-file "supplier-quotes.csv" --open-task "Check currency on row 31 against the supplier quote"
python scripts/validate.py --root "/path/to/work"
python scripts/bootstrap.py --root "/path/to/work"
```

- [checkpoint.py](scripts/checkpoint.py) saves versioned state under `.agent/continuity/`. Use `--source` for the decision's origin and repeat `--decision`, `--context-file`, `--changed-file`, `--blocked-item` and `--open-task` as needed. Attach individual sources to their decisions. Use `--evidence` for shared evidence.
- [validate.py](scripts/validate.py) checks the package, hashes, redaction indicators and writer lock. Review external sources again where they may have changed. Preserve partial review status. Read `handoff.md` and use [bootstrap.py](scripts/bootstrap.py) for the startup prompt.
- For an 80% full migration, first read the source model with `bootstrap.py --show-source-model --thread-id UUID`. Substitute the actual UUID and pass the chosen workspace and target to subsequent commands. Present the detected model in the one confirmation above. After consent, call `bootstrap.py --prepare-thread --inherit-source-model --thread-id UUID`. If the user chose a different model, add `--approved-model OVERRIDE`. Check that the request’s `approved_model` matches what the user approved, then pass it as `model` to Codex `create_thread`. If the source model cannot be verified or has changed since confirmation, keep the source active and ask the user. For an ordinary side chat, ask whether to open it and which model to use together. Once approved, use `bootstrap.py --prepare-thread --approved-model MODEL_ID` and pass the request’s model explicitly. Use the validated prompt when creating the new chat. Record the host's returned ID with [thread_receipt.py](scripts/thread_receipt.py) and `--created-thread-id`, or use `--pending-worktree-id` while setup is pending. Then verify takeover as described above. A failed preparation leaves the source active. A request saved by an earlier attempt applies only to that earlier attempt.
- Hosts with filesystem access can use the same checkpoint. Adjust the startup command to the receiver's available interpreter or host tools. For chat-only environments, provide a copyable handoff using the same fields.
- Use [guard.py](scripts/guard.py) for broader pressure signals such as long logs. Its checkpoint suggestions complement the measured 80% event. See [failure recovery](references/failure-modes.md), [checkpoint schema](references/schema.md) and [three-party review](references/triparty.md) as needed.
