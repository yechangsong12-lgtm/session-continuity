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

- **批量整理和简单搜索。** 直接说“整理这两份价格表”或“查一下这几款产品的规格”即可。Codex 允许根据请求自动选用本技能，是否调用由任务内容和宿主判断。可以指定本次模型、固定以后使用的模型，或让代理按能力与成本选择。子代理把关键结论、来源和明细文件位置带回主对话。
- **上下文达到 80%。** 在 Codex 注册随附 hook 后，默认在界面提醒。希望自动交接时，可以启用本机的 `auto_handoff_at_80` 偏好。启用后，主对话保存并校验交接资料，在支持的客户端创建接手对话。新对话确认已接手后，才询问是否归档旧对话，收到用户同意后执行。Claude Code 提供状态栏提示，用户可在看到提示后发起交接。[配置与宿主差异](skills/session-continuity/references/context-settings.md)
- **交接和接续。** 在当前对话说“用 session-continuity 为这个项目生成交接”，在新对话说“验证同一工作区的交接，从第一项待办继续”。也可在 Codex 输入 `$session-continuity`，或在 Claude Code 输入 `/session-continuity`，再说明目标。

交接文件默认保存在项目的 `.agent/continuity/`。完整步骤见 [技能说明](skills/session-continuity/SKILL.md)。

## 许可

项目使用 [MIT 许可证](LICENSE)。
