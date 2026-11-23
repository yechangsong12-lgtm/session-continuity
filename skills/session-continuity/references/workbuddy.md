# Tencent WorkBuddy Desktop · 腾讯 WorkBuddy 桌面版

## English

**Install and select.** Open the Skills panel under Experts, Skills & Connectors, choose **Add skill → Upload skill**, and import the packaged `session-continuity.zip`. Confirm the skill is enabled in the installed list. For a local development project, you can instead copy the entire skill folder into `.codebuddy/skills/session-continuity/` under the workspace. In a task, select the installed skill in the composer and specify the workspace that holds the work. [Skills](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market) · [Project configuration](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Project) · [Task workspace](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Task-Bar)

**Read the current task.** Use the model selector and context usage ring in the source task. When the displayed usage reaches 80%, ask WorkBuddy to checkpoint in the same task. If the assistant cannot see the reading, supply the current percentage and model, or request a checkpoint at a work boundary. Recheck after compaction. A window tier can reset when the model changes or a new task starts. This skill currently uses the WorkBuddy display for that check. [Model and context controls](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Model)

**Resume an approved transfer.** For example, ask “Use session-continuity to record the verified files and outstanding work in this workspace.” In a local Agent task with Python 3.11+, use `checkpoint.py --source workbuddy` and `validate.py` with the same `--root`. If a full transfer is needed, name the source task’s selected model and ask before opening the successor. After approval, select that model and the same workspace in WorkBuddy, give the new task the validated handoff, and verify its first reply against the revision and an original source. If the receiver lacks workspace access, provide a portable summary and the evidence it needs. For a bounded investigation, return the findings and files to the main task and keep the main task active.

## 简体中文

**安装与选用。** 在「专家·技能·连接器」中打开「技能」，选择「添加技能 → 上传技能」并导入 `session-continuity.zip`，在「已安装」中确认启用。若仅给本地开发项目使用，也可把整份技能复制到工作区的 `.codebuddy/skills/session-continuity/`。在任务输入框选中该技能，并选择实际存放成果的工作空间。[技能管理](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market) · [项目配置](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Project) · [任务工作空间](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Task-Bar)

**查看当前用量。** 在来源任务的模型选择器和上下文用量圆环中查看模型及占用。界面显示用量达到 80% 时，让 WorkBuddy 在原任务存档。如果助手看不到读数，可提供当前百分比与模型，或在阶段完成时要求存档。压缩后重新查看；切换模型或新建任务后，窗口档位可能恢复默认值。本技能在 WorkBuddy 中按界面读数执行该检查。[模型与上下文设置](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Model)

**接续已同意的迁移。** 可以说“用 session-continuity 把已核实的文件和待办保存到当前工作空间”。本地 Agent 模式可使用 Python 3.11+，以相同的 `--root` 运行 `checkpoint.py --source workbuddy` 和 `validate.py`。整项迁移时，先报出原任务当前模型，询问是否开接续任务。用户同意后，在新任务选择已确认的模型和同一工作空间，用已校验的交接资料接续，核对接手方回复中的修订号与一处原始依据。接手方无法访问原工作空间时，提供便携摘要和所需证据。普通旁支完成后，把结论和文件交回主任务，主任务继续保留。
