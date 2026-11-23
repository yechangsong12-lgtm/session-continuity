# Session Continuity · 会话分工与交接

[English](README.md) · 简体中文 · [下载技能包（ZIP）](https://github.com/yechangsong12-lgtm/session-continuity/releases/latest/download/session-continuity.zip)

这是一个给长任务用的对话存档与接续技能。在原对话记下目标、做过的修改、证据位置和第一项未完成的工作。你同意换对话后，**同一个助手里的新对话**从这份记录核实进度，再接着做。

## 到底什么时候开新对话？

| 你要做的事 | Skill 怎么处理 |
| --- | --- |
| “继续”，或“把这套九张商品图里第 06 张的梳齿修短” | 在原对话继续做。 |
| “把这批评论分组，给我主要差评原因” | 可以用后台子代理整理，把结论、来源和明细文件位置交回主对话。 |
| 一份供应商报价有冲突，后面还要等回函、复核、由你决定，其他商品资料可以照常做 | 可以建议**只为这份报价**另开旁支。先说明要拆出的交付物，再问是否开聊、用哪个模型。 |
| 当前对话用量达到 80%，整项任务还没做完 | 按偏好先存档，压缩后重新看用量。如果空间仍紧、剩余任务确需整体接续，再问你是否开新对话。 |

你也可以直接要求开新对话。需要选模型时，你可以自己指定一个可用模型，或明确交给 Agent 判断；已有适用的偏好就沿用。整项迁移时，如果原模型可用，会优先提议沿用。

普通旁支做完，先把结果交回主对话。等两边都结束、证据也已保留，再按你的偏好整理**子对话**。整项迁移中的**原对话**，则要等接手方核验通过，并由你明确同意后才归档。

## 为什么大项目值得考虑 1M 上下文？

大型项目经常在第一次修改前就读入数万 tokens 的项目规则、Markdown 文档和历史决策。以 2026 年 11 月核对的一份 Codex 桌面客户端模型目录为例，GPT‑6.2 Sol 的默认窗口为 500K，Astra 为 272K。按该目录的 95% 有效比例计算，分别是 **475K 和 258.4K**。假设 Astra 已读入 60K 的项目资料，留给接下来的对话、代码和工具结果的空间就只有 **198.4K**。

对话压缩后，摘要可能记得“选了 B”，却省略“为什么否决 A”。窗口更大，助手就有更多空间同时对照原始要求、设计取舍和证据，减少反复解释。在支持的 Codex 模型上，你可以要求设为 **1,000,000 tokens**，并在新会话核实实际窗口。上例的 95% 表示有效窗口比例，自动压缩时机还取决于模型和配置；本技能可在**实际有效窗口用到 80%** 时提前保存进度。[官方模型上限](https://learn.chatgpt.com/docs/models?surface=app) · [压缩设置](https://learn.chatgpt.com/docs/config-file/config-reference) · [1M 配置方法](skills/session-continuity/references/context-settings.md#codex-1m)

## 安装并试用

在你平时使用的助手里安装即可。各客户端分别使用自己的技能入口和上下文读数。

| 客户端 | 安装入口 |
| --- | --- |
| Codex | 把完整技能目录复制到 `~/.agents/skills/` 或项目的 `.agents/skills/`。[可选的 80% 检测](skills/session-continuity/references/context-settings.md) |
| DeepSeek Harness | 使用 `$DSH_HOME/skills/` 或项目的 `.dsh/skills/`。[DSH 指南](skills/session-continuity/references/deepseek-harness.md) |
| 腾讯 WorkBuddy | 从技能面板导入发行 ZIP，或使用项目的 `.codebuddy/skills/`。[WorkBuddy 指南](skills/session-continuity/references/workbuddy.md) |
| Claude 桌面版 | 按 Chat、Cowork 或 Code 标签页选择安装方式。[桌面版指南](skills/session-continuity/references/claude-desktop.md) |
| Claude Code 命令行 | 复制到 `~/.claude/skills/` 或项目的 `.claude/skills/`。[可选的状态栏](skills/session-continuity/references/context-settings.md) |

可以直接说：**“把当前进度存下来，写清查过的证据和第一项没做完的工作。”** 决定换对话时，再让同一助手的新对话核验这份记录并继续。本地脚本需要 Python 3.11+，存档位于工作区的 `.agent/continuity/`。只有聊天文字时，可粘贴交接摘要并附上下一步需要的证据。[完整中文流程](skills/session-continuity/references/workflow.zh-CN.md)

## 项目来源与许可

本项目基于 [r-design-j/codex-session-continuity-skill](https://github.com/r-design-j/codex-session-continuity-skill) 的存档、校验和回执工具开发。仓库与可安装技能包均保留原作者的版权声明和 [MIT 许可证](LICENSE)。

开发者可在仓库根目录运行 `python skills/session-continuity/scripts/self_test.py` 和 `python -m unittest discover -s tests` 复测。
