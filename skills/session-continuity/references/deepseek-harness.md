# DeepSeek Harness (DSH)

## English

**Install and invoke.** Copy the complete `session-continuity` directory to `$DSH_HOME/skills/` (default `~/.dsh/skills/`) for one user, or to `.dsh/skills/` at the project root. DSH also scans the shared user and project `.agents/skills/` roots in its default configuration. It finds the nearest ancestor with `.git`, or uses the working directory when there is none. In a profile with the filesystem provider and skill tool enabled, enter `/session-continuity` or describe the job for automatic discovery. For background work, check `list_subagent_models` when available. The user can pick a route or ask the agent to choose a capable low-cost route. Apply a saved preference only within its agreed scope. If the list is unavailable, ask which routes the user's profile offers. [Skill roots](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/skill/skill-filesystem) · [Skill invocation](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/skill/tool-skill) · [Subagent routes](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/subagent/tool-subagent)

**Check context.** A DSH profile with the token meter exposes `contextPressure.pressureTokens` (latest provider-reported prompt tokens) and `contextWindow`. The separately projected next-prompt size is an estimate, and session-wide token totals cover many requests. Verify the latest completed request in the same top-level chat and on the same provider/model route. If the profile cannot supply a fresh reading, offer a checkpoint at a natural work boundary. [DSH token meter](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/llm/token-meter)

For an independently obtained source ID and its **uncompressed v4 JSONL** file, run this read-only check from the skill directory. With the Web export feature enabled, `/export` provides a ZIP; select the root chat's `session.v4.jsonl`. Keep the archive local because it may include conversations, children and attachments. [DSH session export](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/session-query/session-log-export)

```text
python scripts/dsh_context.py --log "/path/to/session.v4.jsonl" --session-id SOURCE_ID
```

The JSON result identifies the observed provider and model, last settled input tokens (including disjoint cache buckets), window and event sequence. `at_or_above_80` is `true`, `false`, or `null` if evidence is incomplete. A file export documents its capture time; obtain a fresh reading before acting. This command runs on demand. Installing the skill alone does not register a background DSH listener.

**Hand off in DSH.** Use `checkpoint.py --source dsh`, `validate.py` and `bootstrap.py` with the same `--root` and optional `--target`. When a successor session is approved, select the agreed provider/model in DSH and reopen the workspace. Confirm the revision and first source in that session. [Model selection](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/client/ui-model-selection) · [Chat decision rules](../SKILL.md)

## 简体中文

**安装与调用。** 将完整的 `session-continuity` 文件夹复制到用户目录 `$DSH_HOME/skills/`（默认 `~/.dsh/skills/`），或项目根目录的 `.dsh/skills/`。DSH 的默认配置也会扫描用户及项目的共享 `.agents/skills/`。项目根目录取最近带 `.git` 的祖先目录；没有时取当前工作目录。配置中已启用文件系统技能提供器和技能工具时，可输入 `/session-continuity`，也可让宿主根据任务描述选用。后台分工时，可用 `list_subagent_models` 核对当前配置开放的模型。用户可自己选，也可明确交给 Agent 从中选能胜任的低成本模型。已有长期偏好时按其适用范围执行；看不到列表时向用户核对。[技能目录](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/skill/skill-filesystem) · [调用规则](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/skill/tool-skill) · [子代理模型](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/subagent/tool-subagent)

**核对上下文。** 有原生计量器的配置可查看 `contextPressure.pressureTokens`（最近一次服务商返回的提示词用量）与 `contextWindow`。预计下次请求的用量属于估算；累计费用用量覆盖多次请求。应核对同一顶层会话、同一服务商和模型的最新已完成请求。拿不到新读数时，可以在工作阶段结束时建议存档。[DSH 原生计量说明](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/llm/token-meter)

从 DSH 独立取得源会话 ID，打开该会话的**未压缩 v4 JSONL** 文件，再运行上面的只读命令。已启用 Web 导出的配置可用 `/export` 下载 ZIP，选根会话的 `session.v4.jsonl`。压缩包可能含聊天内容、子会话和附件，应在本地核验。输出包括观测到的服务商、模型、最近已结算的输入用量（含独立缓存计数）、窗口和事件序号。`at_or_above_80` 为 `true`、`false` 或表示缺少依据的 `null`。导出件反映导出当时的状态，执行前须重新核对。该工具按需运行，单独复制 Skill 后不会自动注册 DSH 后台监听器。[会话导出](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/session-query/session-log-export)

**在 DSH 中交接。** 在同一工作区使用 `checkpoint.py --source dsh`、`validate.py` 和 `bootstrap.py`，沿用同一 `--root` 及可选的 `--target`。新开接续会话获同意后，在 DSH 选择已确认的服务商与模型，打开该工作区并复查交接修订和一项原始依据。[DSH 模型选择](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/client/ui-model-selection) · [开聊与归档条件](workflow.zh-CN.md)
