# Session Continuity · 会话分工与交接

[English](README.md) · 简体中文 · [下载可直接导入的技能包（ZIP）](https://github.com/yechangsong12-lgtm/session-continuity/releases/latest/download/session-continuity.zip)

换一个对话，甚至换一个 AI 助手，也能接着做同一件事。Session Continuity 会记下用户的目标、已经确定的事情、证据的位置，以及下一步要做什么。接手方能访问工作区时，可以核对交接版本，打开原始文件，再从第一项待办开始。

比如，你在 WorkBuddy 里对了两份供应商报价，想换到 Claude 桌面版复核差价。交接摘要可以指出两份表分别是哪一行、哪个价格还没确认，以及接下来要向供应商核对什么。若只是改一张图，或者你只说“继续”，就留在原对话完成。

## 选择你使用的助手

| 助手 | 安装入口 | 如何查看用量、接续任务 |
| --- | --- | --- |
| Codex | 把技能复制到用户的 `~/.agents/skills/` 或项目的 `.agents/skills/`。[官方技能说明](https://developers.openai.com/codex/skills) | 可选的本地 Hook 检测 80% 用量。可以启用自动存档；整项迁移前仍会向你确认。[配置方法](skills/session-continuity/references/context-settings.md) |
| DeepSeek Harness（DSH） | 安装到 `$DSH_HOME/skills/` 或 Git 项目的 `.dsh/skills/`。[DSH 接入指南](skills/session-continuity/references/deepseek-harness.md) | 在工作区调用 `/session-continuity`，按 DSH 自己的会话数据判断上下文占用。 |
| 腾讯 WorkBuddy | 在技能面板上传 ZIP，或使用项目的 `.codebuddy/skills/`。[WorkBuddy 接入指南](skills/session-continuity/references/workbuddy.md) | 查看当前任务的上下文用量圆环和模型，在接手任务能打开的工作空间里存档。 |
| Claude 桌面版 | Chat 或 Cowork 从技能设置上传 ZIP；本地 Code 标签页也可以读取 Claude Code 技能目录。[按模式查看安装步骤](skills/session-continuity/references/claude-desktop.md) | Chat 可接收摘要和相关文件，Cowork 可连接工作文件夹，Code 标签页可查看当前会话占用。 |
| Claude Code 命令行 | 复制到用户的 `~/.claude/skills/` 或项目的 `.claude/skills/`。[官方技能说明](https://code.claude.com/docs/en/skills) | 使用 `/session-continuity`。按需配置状态栏，达到 80% 时显示提示。[配置方法](skills/session-continuity/references/context-settings.md) |

按目录安装时，复制完整的 `skills/session-continuity/`，保留其中的许可证。安装后的入口是 `session-continuity/SKILL.md`。随附脚本使用 Python 3.11+ 标准库。页面顶部的 ZIP 已按技能导入格式打包。

## 试一次交接

1. **在原对话存档。** 可以直接说：“准备一份交接，写明查过哪些文件、哪些问题还没定、接手后的第一步是什么。”本地工作区的交接资料保存在 `.agent/continuity/`。
2. **决定在哪里继续。** 日常任务留在主对话。宿主支持后台子代理时，可让低成本模型处理有明确范围的整理和检索，再交回结论、来源与明细。需要你单独跟进的旁支，会先问是否开新对话、用哪个模型。80% 时若确实要整体迁移，目标端支持原模型才提议沿用。原模型不可用时，你可以从目标端当前账号的可用项里指定一个，也可以明确让 Agent 自行判断；已有适用的长期偏好就沿用。
3. **让接手方核实。** 在新对话里打开同一工作区，说：“验证交接版本，复查第一项待办的依据，然后继续。”两个助手看到的磁盘路径不同时，可以在来源端的技能目录导出一份可直接粘贴的摘要：

   ```sh
   python scripts/bootstrap.py --root "/path/to/work" --portable --output handoff.md
   ```

   把摘要和相应证据交给接手方。只能看到聊天文字时，接手方应说清实际读到了什么。校验通过说明交接文件完整；涉及价格、数量等关键数字，仍需回查原表。

普通旁支会把结果交回主对话。主任务和旁支都结束、证据已保留时，再按你的偏好整理子对话。整项迁移后，只有接手方确认接手并得到你的同意，才归档原对话。[完整中文流程](skills/session-continuity/references/workflow.zh-CN.md)

## 项目来源与许可

本项目基于 [r-design-j/codex-session-continuity-skill](https://github.com/r-design-j/codex-session-continuity-skill) 的存档、校验、接续与回执工具开发。本版本维护中英文流程、客户端接入、上下文提醒和模型确认。仓库与可安装技能包均保留上游版权声明。[MIT 许可证](LICENSE)
