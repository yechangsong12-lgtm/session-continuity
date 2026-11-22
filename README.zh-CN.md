# Session Continuity · 会话交接

[English](README.md) · 简体中文

支持简体中文和英语的长任务交接技能，适用于 Codex 和 Claude Code。它把批量调查交给子代理，将结论和来源带回主对话，并把目标、证据、待办和第一步操作写入工作区。下一位协作者可以用这些材料接续任务。

## 安装

运行随附脚本需要 Python 3.11 或更高版本。下载仓库后，把整个 `skills/session-continuity` 文件夹复制到所选目录，使 `SKILL.md` 位于表中路径。

| 客户端 | 对当前用户生效 | 仅对当前项目生效 |
| --- | --- | --- |
| Codex | `~/.agents/skills/session-continuity/SKILL.md` | `.agents/skills/session-continuity/SKILL.md` |
| Claude Code | `~/.claude/skills/session-continuity/SKILL.md` | `.claude/skills/session-continuity/SKILL.md` |

`~` 表示用户主目录。客户端的技能发现和调用规则见 [Codex 官方说明](https://developers.openai.com/codex/skills) 和 [Claude Code 官方说明](https://code.claude.com/docs/en/skills)。

## 使用

- **批量整理和简单搜索。** 直接说“整理这两份价格表”或“查一下这几款产品的规格”即可。Codex 允许根据请求自动选用本技能，是否调用由任务内容和宿主判断。可以指定本次模型、固定以后使用的模型，或让代理按能力与成本选择。子代理把关键结论、来源和明细文件位置带回主对话。
- **是否另开对话。** “继续”、修一张图、同一份交付物的小改都在当前对话完成。需要独立跟进的旁支，先询问是否另开和使用哪个模型，得到同意后才创建。子对话的结论和证据先交回主对话。主任务与旁支均已完成，且子对话没有待办、待审、独有证据和保留要求时，用户已授权自动整理可归档该子对话；否则询问是否归档这个具体子对话。普通旁支的主对话始终保留。
- **上下文达到 80%。** 在 Codex 注册随附 hook 后，默认在界面提醒。希望自动保存现场时，可以启用本机的 `auto_checkpoint_at_80` 偏好。启用后可自动保存并校验交接资料。整项迁移会读取原对话实际模型 X，再问一句“要沿用原对话的 X 模型开接续对话吗？也可换模型。”只需确认本次开聊即可沿用当前模型。创建后会核实接收方实际模型。说“继续”仍在原对话执行。仅在真实来源已达 80% 且仍需整体迁移、整个主任务已交接、新对话已确认接手时，才询问是否归档原对话，收到明确同意后执行。询问前会再次测量当前占用。压缩后占用已回落或原对话仍有工作时，保留原对话。Claude Code 提供状态栏提示，用户可在看到提示后发起交接。[配置与宿主差异](skills/session-continuity/references/context-settings.md)
- **交接和接续。** 在当前对话说“用 session-continuity 为这个项目生成交接”，在新对话说“验证同一工作区的交接，从第一项待办继续”。也可在 Codex 输入 `$session-continuity`，或在 Claude Code 输入 `/session-continuity`，再说明目标。

交接文件默认保存在项目的 `.agent/continuity/`。完整步骤见[中文技能说明](skills/session-continuity/references/workflow.zh-CN.md)。

## 许可

项目使用 [MIT 许可证](LICENSE)。
