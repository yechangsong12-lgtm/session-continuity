# Codex 上下文窗口与提醒

## 读取、调整和复核窗口

在安装后的技能目录运行以下命令。脚本要求 Python 3.11 或以上。macOS、Linux 可用 `python3`，Windows 可用能启动对应版本的 `py -3` 或 Python 解释器的绝对路径。

```text
python3 scripts/context_window.py
python3 scripts/context_window.py --config /path/to/test-config.toml
python3 scripts/context_window.py --set <用户明确指定的正整数>
```

默认读取 `$CODEX_HOME/config.toml`，变量未设置时读取用户目录的 `.codex/config.toml`。查询只输出根级 `model_context_window` 或 `unset`。仅在用户明确给出新数值时使用 `--set`。脚本校验 TOML，保留其他配置、注释与换行。用 `--config` 可在临时副本测试，也可指向用户明确指定的配置文件。未设置根级配置时，实际窗口取决于活动模型和有效配置层。

调整前查阅活动模型的支持范围。写入后重新读配置，再重启 Codex 或启动加载了新配置的会话，确认实际模型与窗口。桌面版和 CLI 的输入框可用 `/status` 查看当前聊天上下文使用情况。需要核对精确窗口时，从该聊天对应的本地会话日志读取最近一条可用 `token_count`，查看 `info.model_context_window`。这可能与配置值不同。读取时只提取所需数字。

`model_context_window` 配置窗口，`model_auto_compact_token_limit` 配置常规自动压缩的 token 阈值，后者未设置时使用模型默认值。`model_post_turn_compact_threshold_percent` 可在最终回复后按可用窗口的百分比触发压缩，省略或为 `0` 时关闭这一回合结束触发方式。80% 提醒由下方 hook 独立判断。 [Codex 配置参考](https://learn.chatgpt.com/docs/config-file/config-reference) · [模型与窗口](https://learn.chatgpt.com/docs/models) · [桌面斜杠命令](https://learn.chatgpt.com/docs/reference/slash-commands) · [CLI 命令](https://learn.chatgpt.com/docs/developer-commands?surface=cli#inspect-the-session-with-status)

## 80% 提醒的采样

`scripts/context-reminder.py` 是可安装的 Codex 命令 hook。它校验当前聊天的本地日志路径和会话 ID，使用最近一条可用样本的 `info.last_token_usage.total_tokens / info.model_context_window`。这是最近一次模型请求的用量比例，桌面显示可能采用不同的估算。持续达到或超过 80% 时，每个聊天只提示一次。观察到低于阈值的样本或压缩记录后，会清除该聊天的去重状态。只有在 hook 事件触发且已有可用样本时才会检查。

提醒以界面提示显示。后续工作照常进行。用户明确要求交接时，再按本技能的交接流程执行。

## 为另一套本地 Codex 安装

已有同一提醒注册的环境可直接使用。其他环境可按以下步骤安装。

1. 将技能内的 `scripts/context-reminder.py` 复制到该环境 Codex 用户目录下的 `hooks/context-reminder.py`。查看脚本正文，并确认解释器来自可信安装。推荐使用 Python 3.11 或以上的绝对路径，避免桌面应用的 PATH 与终端不同。macOS、Linux 可用 `command -v python3` 查找，Windows PowerShell 可用 `py -3 -c "import sys; print(sys.executable)"` 查找。
2. 在该环境的 `$CODEX_HOME/hooks.json` 注册。未设置 `CODEX_HOME` 时，macOS、Linux 使用 `~/.codex/hooks.json`，Windows 使用 `%USERPROFILE%\.codex\hooks.json`。如果同一用户配置层已用 `config.toml` 的 `[hooks]`，沿用它和官方文档的 TOML 结构。若使用现有 `hooks.json`，把相应事件组追加到已有事件数组，保留其他事件、事件组和顶层字段。只在新文件中使用完整示例。相同脚本与事件只注册一次。
3. 在命令中将示例解释器和脚本路径替换成各自实际的绝对路径。Windows 可用正斜线表示路径，并使用 `commandWindows` 指定 Windows 命令。以下是注册于四个事件的有效 JSON 结构。

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {"hooks": [{"type": "command", "command": "\"/path/to/python3\" -B -X utf8 \"/path/to/codex/hooks/context-reminder.py\"", "commandWindows": "\"C:/Path To Python/python.exe\" -B -X utf8 \"C:/Path To Codex/hooks/context-reminder.py\"", "timeout": 5}]}
    ],
    "PostToolUse": [
      {"hooks": [{"type": "command", "command": "\"/path/to/python3\" -B -X utf8 \"/path/to/codex/hooks/context-reminder.py\"", "commandWindows": "\"C:/Path To Python/python.exe\" -B -X utf8 \"C:/Path To Codex/hooks/context-reminder.py\"", "timeout": 5}]}
    ],
    "Stop": [
      {"hooks": [{"type": "command", "command": "\"/path/to/python3\" -B -X utf8 \"/path/to/codex/hooks/context-reminder.py\"", "commandWindows": "\"C:/Path To Python/python.exe\" -B -X utf8 \"C:/Path To Codex/hooks/context-reminder.py\"", "timeout": 5}]}
    ],
    "PreCompact": [
      {"hooks": [{"type": "command", "command": "\"/path/to/python3\" -B -X utf8 \"/path/to/codex/hooks/context-reminder.py\"", "commandWindows": "\"C:/Path To Python/python.exe\" -B -X utf8 \"C:/Path To Codex/hooks/context-reminder.py\"", "timeout": 5}]}
    ]
  }
}
```

4. 重新加载 Codex。在 CLI 输入 `/hooks`，或在桌面版打开设置中的 Hooks，也可在输入区选择 Review hooks。核对来源、事件和命令后，仅信任已审查的提醒。Hooks 默认开启。若主动关闭过且想恢复，可在现有 `[features]` 表设置 `hooks = true`，并遵守受管配置。 [Hooks 安装、信任与禁用](https://learn.chatgpt.com/docs/hooks)

可在终端将 `{}` 通过标准输入传给脚本，确认解释器能执行，预期为退出成功且无输出。缺少可用日志、格式已变、客户端不支持本地命令 hook 或策略限制时，可使用 `/status` 手动查看上下文。Codex 官方将本地日志格式视为可变实现。 [Hook 输入与输出](https://learn.chatgpt.com/docs/hooks#common-input-fields)

## Claude Code 的 80% 状态栏提示

Claude Code 官方 `statusLine` 会把 JSON 传到配置命令的标准输入。`scripts/claude_context_status.py` 直接读取 `context_window.used_percentage`。达到 80% 时，状态栏持续显示交接提示，回落后自动隐藏。低于阈值时，脚本默认显示普通使用率，`--reminder-only` 则静默。字段缺失、为 `null` 或格式无效时均静默。这个提示随 Claude 的状态栏刷新显示，Codex 的一次性事件提示由上面的 hook 提供。 [Claude Code 状态栏](https://code.claude.com/docs/en/statusline#context-window-fields)

### 独立状态栏

将脚本保存在本机可读的固定位置。编辑 Claude Code 用户设置 `~/.claude/settings.json`，也可选项目设置 `.claude/settings.json`。保留其他设置，将以下字段合入根级对象。将占位路径替换为实际绝对路径，Windows 可用 `C:/...` 形式。Python 可参照上文选择已安装的 3.11+ 解释器。 [手动配置状态栏](https://code.claude.com/docs/en/statusline#manually-configure-a-status-line)

```json
{
  "statusLine": {
    "type": "command",
    "command": "\"/absolute/path/to/python3\" -B -X utf8 \"/absolute/path/to/claude_context_status.py\""
  }
}
```

### 保留已有状态栏

在已有脚本中将标准输入一次读入变量，让现有逻辑和提醒脚本各自读取同一份 JSON，最后仅在提醒有内容时拼接。若现有 `command` 是一条内联命令，可将其移入包装脚本，再把 `statusLine.command` 指向包装脚本，保留原状态栏的其他字段。以下命令中的路径均需替换。

macOS、Linux 或 Git Bash 包装脚本示例。

```bash
#!/usr/bin/env bash
input=$(cat)
base=$(printf '%s' "$input" | "/path/to/existing-statusline")
reminder=$(printf '%s' "$input" | "/path/to/python3" -B -X utf8 "/path/to/claude_context_status.py" --reminder-only)
[ -z "$reminder" ] || base="${base:+$base | }$reminder"
printf '%s\n' "$base"
```

Windows PowerShell 包装脚本示例。可用官方格式将 `statusLine.command` 指向 `powershell -NoProfile -File \"C:/path/to/wrapper.ps1\"`。

```powershell
$payload = $input | Out-String
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding
$base = ($payload | & 'C:/path/to/existing-statusline.ps1' 6>&1) -join "`n"
$reminder = $payload | & 'C:/path/to/python.exe' -B -X utf8 'C:/path/to/claude_context_status.py' --reminder-only
if ($base -and $reminder) { "$base | $reminder" } elseif ($reminder) { $reminder } else { $base }
```

可用合成 JSON 验证脚本或包装命令。把 `{"context_window":{"used_percentage":80}}` 传入应出现提示，改为 `79` 时组合模式应无新增内容，改为 `null` 时两种模式均无提醒输出。若客户端或受管设置禁用了自定义状态栏，可在 Claude Code 运行 `/context` 手动查看占用。 [Windows 配置](https://code.claude.com/docs/en/statusline#windows-configuration) · [Claude Code 命令](https://code.claude.com/docs/en/commands)
