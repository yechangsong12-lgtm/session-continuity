# Session Continuity

给 Codex 和 Claude Code 使用的长任务交接技能。它把批量调查交给子代理，将结论和来源带回主对话，并把目标、证据、待办和第一步操作写入工作区。下一位协作者可以用这些材料接续任务。

## 安装

运行随附脚本需要 Python 3.11 或更高版本。下载仓库后，把整个 `skills/session-continuity` 文件夹复制到所选目录，使 `SKILL.md` 位于表中路径。

| 客户端 | 对当前用户生效 | 仅对当前项目生效 |
| --- | --- | --- |
| Codex | `~/.agents/skills/session-continuity/SKILL.md` | `.agents/skills/session-continuity/SKILL.md` |
| Claude Code | `~/.claude/skills/session-continuity/SKILL.md` | `.claude/skills/session-continuity/SKILL.md` |

`~` 表示用户主目录。客户端的技能发现和调用规则见 [Codex 官方说明](https://developers.openai.com/codex/skills) 和 [Claude Code 官方说明](https://code.claude.com/docs/en/skills)。

## 使用

- **批量调研。** 可以说“把这批搜索交给低 token 成本的子代理，汇总发现、来源和明细位置”。由使用者指定本次模型、沿用已选的固定模型，或让代理从当前宿主可用模型中自动选择。使用者已有偏好时直接沿用。需要独立追踪的任务会建议另开对话。
- **上下文管理。** 可以说“检查当前上下文窗口和 80% 提醒”。在 Codex 中，要得到事件触发的提醒，还需向客户端注册相应 Hook；技能会引导检查实际配置和读数。Claude Code 可用随附脚本在状态栏显示上下文占用，达到 80% 时持续显示交接提示，回落后自动隐藏。两种安装方法见[上下文窗口与提醒](skills/session-continuity/references/context-settings.md)。窗口设置、用量来源和通知能力取决于客户端及模型。
- **交接和接续。** 在当前对话说“用 session-continuity 为这个项目生成交接”，在新对话说“验证同一工作区的交接，从第一项待办继续”。也可在 Codex 输入 `$session-continuity`，或在 Claude Code 输入 `/session-continuity`，再说明目标。

交接文件默认保存在项目的 `.agent/continuity/`。完整步骤见 [技能说明](skills/session-continuity/SKILL.md)。

## 许可

项目使用 [MIT 许可证](LICENSE)。
