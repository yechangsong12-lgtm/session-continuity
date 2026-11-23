# Tencent WorkBuddy Desktop · 腾讯 WorkBuddy 桌面版

## English

**Install and select.** Open the Skills panel under Experts, Skills & Connectors, choose **Add skill → Upload skill**, and import the packaged `session-continuity.zip`. Confirm the skill is enabled in the installed list. For a local development project, you can instead copy the entire skill folder into `.codebuddy/skills/session-continuity/` under the workspace. In a task, select the installed skill in the composer and specify the workspace that holds the work. [Skills](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market) · [Project configuration](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Project) · [Task workspace](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Task-Bar)

**Read the current task.** Use the model selector and context usage ring in the source task. When the displayed usage reaches 80%, ask WorkBuddy to checkpoint in the same task. If the assistant cannot see the reading, supply the current percentage and model, or request a checkpoint at a work boundary. Recheck after compaction. A window tier can reset when the model changes or a new task starts. This skill currently uses the WorkBuddy display for that check. [Model and context controls](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Model)

**Resume in WorkBuddy.** Save in the task workspace with `checkpoint.py --source workbuddy` and validate using the same `--root`. After the user confirms a new task and model, select that model and the same workspace. Ask the new task to verify the saved revision and one source for the first open item. [When to open or archive a chat](../SKILL.md)

## 简体中文

**安装与选用。** 在「专家·技能·连接器」中打开「技能」，选择「添加技能 → 上传技能」并导入 `session-continuity.zip`，在「已安装」中确认启用。若仅给本地开发项目使用，也可把整份技能复制到工作区的 `.codebuddy/skills/session-continuity/`。在任务输入框选中该技能，并选择实际存放成果的工作空间。[技能管理](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market) · [项目配置](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Project) · [任务工作空间](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Task-Bar)

**查看当前用量。** 在来源任务的模型选择器和上下文用量圆环中查看模型及占用。界面显示用量达到 80% 时，让 WorkBuddy 在原任务存档。如果助手看不到读数，可提供当前百分比与模型，或在阶段完成时要求存档。压缩后重新查看；切换模型或新建任务后，窗口档位可能恢复默认值。本技能在 WorkBuddy 中按界面读数执行该检查。[模型与上下文设置](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Model)

**在 WorkBuddy 中接续。** 在任务工作区用 `checkpoint.py --source workbuddy` 存档，并用同一 `--root` 校验。用户同意开新任务并确认模型后，选择该模型和同一工作空间，请接手任务核对存档修订及第一项待办所依据的原始资料。[开聊与归档条件](workflow.zh-CN.md)
