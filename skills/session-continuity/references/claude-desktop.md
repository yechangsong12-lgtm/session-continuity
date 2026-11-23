# Claude Desktop

English · [简体中文](#简体中文)

Choose instructions for the **environment where the task runs**. Some Desktop versions combine Chat and Cowork in one interface. Folder access and the selected coding environment determine how a successor can reach the evidence. [Chat and Cowork in Claude](https://support.claude.com/en/articles/16761823-claude-cowork-and-chat-are-one-claude)

| Surface | Set up the skill | Resume a task |
| --- | --- | --- |
| Chat | Upload the skill ZIP in your Claude account, as described below. | Ask for a handoff message. After you approve opening a chat and select a model or delegate the choice, paste the message there and attach the evidence it needs. |
| Cowork or a chat working with a connected folder | Use the account skill and grant access to the relevant folder. | Save the checkpoint or readable handoff in the connected folder. In the receiving session, reopen that folder and check that the files are accessible. A cloud session reaches connected local files through the running Desktop app. [Cowork file access](https://support.claude.com/en/articles/15520349-use-claude-cowork-on-web-desktop-and-mobile) |
| Code tab | Local sessions can discover the full folder at `~/.claude/skills/session-continuity/` or `.claude/skills/session-continuity/` in the project. SSH uses the remote host’s paths. Cloud sessions load enabled account skills. | Select the shared workspace and invoke `/session-continuity`. Check the actual model in the picker. In the Code tab, `/context` or **Session details → Context** shows the current session’s usage. [Code skills](https://code.claude.com/docs/en/desktop#use-skills) · [Code context meter](https://code.claude.com/docs/en/desktop#check-usage) |

### Upload for Chat and Cowork

Download [session-continuity.zip](https://github.com/yechangsong12-lgtm/session-continuity/releases/latest/download/session-continuity.zip). In **Customize → Skills**, select **+ → Create skill → Upload a skill**, choose the ZIP and enable it. Individual accounts need file creation and code execution enabled under **Settings → Capabilities**. Managed accounts also follow their organization's Skills and cloud code execution policy. [Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude)

The archive starts with `session-continuity/SKILL.md`; the license, references and scripts sit alongside it in that directory. [Anthropic’s packaging guide](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills)

### Try a handoff

Ask: “Prepare a handoff for the current task. Include the source for the first open item and the first check the next session should perform.” With shared files and Python 3.11+, use the checkpoint and validation commands in the [main workflow](../SKILL.md). To export a prompt for a different environment, run `python scripts/bootstrap.py --root "/path/to/work" --portable` from the skill folder. Give the successor the referenced evidence in a location it can open. With chat text alone, ask it to name the source and its next action; report a verified checkpoint revision only after it can open and validate the saved package.

A real session reading of 80% can prompt a checkpoint. Without a reliable reading, offer one at a work boundary. Check the model picker in the receiving account and surface (Chat, Cowork or Code). Offer to keep the source model only if it is selectable there. Apply any in-scope standing choice, or let the user select a verified option or explicitly ask the agent to choose. If the picker is hidden, ask what the user sees; if it lists a single model, name it. Confirm opening the new chat separately. The [terminal status-line adapter](context-settings.en.md) is optional for Claude Code CLI users. This Desktop workflow does not rely on a custom status line appearing in Chat or Cowork.

## 简体中文

以**任务实际运行环境**为准。部分桌面版已把 Chat 和 Cowork 合并到同一界面，接手时先确认双方可以访问哪些文件。[桌面版 Chat 与 Cowork](https://support.claude.com/en/articles/16761823-claude-cowork-and-chat-are-one-claude)

| 工作环境 | 安装与调用 | 如何接手 |
| --- | --- | --- |
| 普通 Chat | 在 Claude 账号中上传并启用 Skill。 | 请 Claude 整理可粘贴的交接摘要。你同意开聊并指定模型或明确委托选择后，把摘要和下一步所需的证据一起交给新对话。 |
| Cowork 或已连接文件夹的对话 | 使用账号内的 Skill，连接本次任务需要的文件夹。 | 把交接包或可读摘要保存在已连接目录。接手方打开相同目录并确认可读。云端任务访问本机文件时，桌面应用需要运行并保持连接。[Cowork 文件访问](https://support.claude.com/en/articles/15520349-use-claude-cowork-on-web-desktop-and-mobile) |
| Code 标签页 | 本地环境可从用户级 `~/.claude/skills/session-continuity/` 或项目级 `.claude/skills/session-continuity/` 加载完整技能。SSH 使用远端路径，云端会话加载账号内已启用的技能。 | 在相同工作区调用 `/session-continuity`。从模型选择器核对实际模型，用 `/context` 或会话详情的 **Context** 卡片检查当前会话的上下文占用。[Code 技能](https://code.claude.com/docs/en/desktop#use-skills) · [上下文读数](https://code.claude.com/docs/en/desktop#check-usage) |

### 给 Chat 和 Cowork 安装

下载 [session-continuity.zip](https://github.com/yechangsong12-lgtm/session-continuity/releases/latest/download/session-continuity.zip)。进入 **Customize → Skills → + → Create skill → Upload a skill**，选择压缩包并启用。个人账号在 **Settings → Capabilities** 启用文件创建与代码执行；团队账号还需符合组织设置。压缩包以 `session-continuity/SKILL.md` 为入口，目录内保留许可证、参考说明和脚本。[Claude 技能设置](https://support.claude.com/en/articles/12512180-use-skills-in-claude) · [官方打包示例](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills)

### 试一次交接

可以说：“整理当前任务的交接，附上第一项待办的证据和接手后最先要核对的内容。”有共享工作区和 Python 3.11+ 时，按[中文流程](workflow.zh-CN.md)保存并校验交接包。从技能目录执行 `python scripts/bootstrap.py --root "/path/to/work" --portable` 可导出跨环境的接手提示。把对应证据放到接手方能打开的位置；仅有聊天文本时，用对方实际读到的来源和下一步确认接手。有完整交接包且校验成功后，才报告已验证的修订号。

当前会话实际用量达到 80% 时可以存档，没有可靠读数时就在阶段结束时提示。先核对目标账号及 Chat、Cowork 或 Code 对应选择器里的模型；原模型在目标可选时才提议沿用。已有适用偏好时沿用，或请用户从可用选项中指定、明确委托 Agent 选择。看不到列表就向用户核对；只有一个选项就说明。开可见对话仍需单独同意。Claude Code 命令行的[状态栏适配器](context-settings.md)可单独配置，Chat 和 Cowork 通过上述流程使用。
