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

Ask Claude to record the goal, checked evidence and first open item. In a new Claude chat, reopen the same folder and validate the expected revision. For text-only use, paste the handoff and attach the evidence the next step requires. The receiver should say which files it could actually inspect. [Full workflow](../SKILL.md)

Use the reading available in the current mode or checkpoint at a work boundary. Check the model selector for that mode before opening a successor. [Optional terminal status line](context-settings.en.md#configure-the-claude-code-status-line)

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

让 Claude 写明任务目标、已查证的依据和第一项待办。新 Claude 对话打开同一文件夹后核验预期修订；只能传文字时，粘贴交接摘要并附上下一步需要的原始资料。接手方说明实际看到了哪些文件。[完整流程](workflow.zh-CN.md)

按当前模式的真实读数或阶段节点存档。开接续对话前核对该模式的模型选择器。[可选的命令行状态栏](context-settings.md)
