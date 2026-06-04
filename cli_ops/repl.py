# -*- coding: utf-8 -*-
"""
交互式 REPL 引擎
================
类似 Claude Code 的终端交互体验：斜杠命令、rich 渲染、会话上下文。

设计原则：
  - 无参数进入 REPL，有参数走传统 argparse 模式
  - 斜杠命令 /xxx 映射到现有 cmd_* 函数
  - 支持命令别名和快捷键
  - readline 历史记录和 Tab 补全
"""

import os
import sys
import shlex
import argparse
from typing import Any, Dict, List, Optional

from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich import box

from .session import session
from .rich_ui import (
    console, render_header, render_success, render_error,
    render_warning, render_info, render_kv, render_kv_table,
    render_table, render_badge, render_status_line,
    render_divider, render_blank,
)

# ============================================================================
# readline 初始化
# ============================================================================

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "..", ".cli_ops_history")
_READLINE_OK = False

try:
    import readline
    _READLINE_OK = True

    def _rl_completer(text: str, state: int) -> Optional[str]:
        matches = [c for c in ALL_COMMANDS if c.startswith(text)]
        matches.append(None)
        return matches[state]

    readline.set_completer(_rl_completer)
    readline.set_completer_delims(" \t\n")
    # Tab 补全
    if "libedit" not in readline.__doc__:
        readline.parse_and_bind("tab: complete")
    else:
        readline.parse_and_bind("bind ^I rl_complete")

    if os.path.exists(HISTORY_FILE):
        try:
            readline.read_history_file(HISTORY_FILE)
        except Exception:
            pass
except (ImportError, ModuleNotFoundError):
    pass


def _save_history() -> None:
    if _READLINE_OK:
        try:
            readline.write_history_file(HISTORY_FILE)
        except Exception:
            pass


# ============================================================================
# 命令别名 & 快捷键
# ============================================================================

SHORTCUTS: Dict[str, str] = {
    "s": "status",
    "sc": "scan",
    "e": "export",
    "cc": "clear-cache",
    "le": "list-exports",
    "cr": "check-rag",
    "br": "build-rag",
    "t": "test",
    "h": "health",
    "r": "report",
    "ms": "monitor-snap",
    "cl": "clean-logs",
    "b": "backup",
    "ci": "config-info",
    "q": "quit",
}

# 命令别名（常用参数组合）
ARG_ALIASES: Dict[str, str] = {
    "scan poems": "--dir ./poem_json",
    "export csv": "--format csv",
    "export json": "--format json",
    "export xml": "--format xml",
    "export txt": "--format txt",
    "export html": "--format html",
    "report text": "--format text",
    "report json": "--format json",
    "report html": "--format html",
}

# 所有可补全的命令（含别名）
ALL_COMMANDS = sorted(set(
    list(SHORTCUTS.keys()) +
    [f"/{k}" for k in SHORTCUTS] +
    ["/" + c for c in [
        "status", "scan", "export", "clear-cache", "list-exports",
        "check-rag", "build-rag", "test", "health", "report",
        "monitor-snap", "clean-logs", "backup", "config-info",
        "help", "quit", "exit",
    ]]
))


# ============================================================================
# 欢迎界面
# ============================================================================

def _print_welcome() -> None:
    logo = Text()
    logo.append("╔══════════════════════════════════════════════════════╗\n", style="cyan")
    logo.append("║                                                      ║\n", style="cyan")
    logo.append("║   ", style="cyan")
    logo.append("唐诗意象数据运维管理系统", style="bold white")
    logo.append("                              ║\n", style="cyan")
    logo.append("║   ", style="cyan")
    logo.append("CLI Operations Toolkit  v1.0", style="dim")
    logo.append("                         ║\n", style="cyan")
    logo.append("║                                                      ║\n", style="cyan")
    logo.append("╚══════════════════════════════════════════════════════╝", style="cyan")

    tips = Text()
    tips.append("\n  输入 ", style="dim")
    tips.append("/help", style="bold cyan")
    tips.append(" 查看命令    ", style="dim")
    tips.append("/status", style="bold cyan")
    tips.append(" 系统概览    ", style="dim")
    tips.append("/scan", style="bold cyan")
    tips.append(" 扫描数据\n", style="dim")
    tips.append("  Ctrl+D 或 ", style="dim")
    tips.append("/quit", style="bold cyan")
    tips.append(" 退出\n", style="dim")

    console.print(logo)
    console.print(tips)


# ============================================================================
# 命令解析
# ============================================================================

def _parse_slash_input(raw: str) -> Optional[argparse.Namespace]:
    """解析斜杠命令输入，返回 argparse.Namespace 或 None（无效命令）"""
    raw = raw.strip()

    # 移除前导 /
    if raw.startswith("/"):
        raw = raw[1:]
    else:
        return None

    if not raw:
        return None

    # 分割命令和参数
    parts = shlex.split(raw)
    cmd_name = parts[0].lower()
    args_list = parts[1:] if len(parts) > 1 else []

    # 应用快捷键
    if cmd_name in SHORTCUTS:
        cmd_name = SHORTCUTS[cmd_name]

    # 应用参数别名
    alias_key = f"{cmd_name} {' '.join(args_list)}"
    if alias_key in ARG_ALIASES:
        args_list = shlex.split(ARG_ALIASES[alias_key])

    # 检查是否是退出命令
    if cmd_name in ("quit", "exit", "q"):
        return argparse.Namespace(command="quit")

    if cmd_name == "help":
        return argparse.Namespace(command="help", topic=args_list[0] if args_list else "")

    # 从 cli_main 加载命令表
    from .cli_main import COMMANDS, create_parser
    if cmd_name not in COMMANDS:
        console.print(f"\n  [red]未知命令:[/red] {cmd_name}")
        _suggest_command(cmd_name)
        return None

    # 用 argparse 解析参数
    parser = create_parser()
    try:
        full_args = [cmd_name] + args_list
        parsed = parser.parse_args(full_args)
        return parsed
    except SystemExit:
        return None


def _suggest_command(partial: str) -> None:
    """模糊匹配建议"""
    from .cli_main import COMMANDS
    suggestions = [c for c in COMMANDS if partial in c or partial[:3] in c]
    if suggestions:
        cmds = ", ".join(f"[cyan]/{c}[/cyan]" for c in suggestions[:3])
        console.print(f"  试试: {cmds}")
    console.print(f"  输入 [cyan]/help[/cyan] 查看全部命令")


# ============================================================================
# /help 命令
# ============================================================================

def _show_help(topic: str = "") -> None:
    from .cli_main import COMMANDS

    if topic:
        if topic in COMMANDS:
            _, desc = COMMANDS[topic]
            content = Text()
            content.append(f"\n  /{topic}\n", style="bold cyan")
            content.append(f"  {desc}\n", style="dim")
            console.print(content)
        else:
            render_error(f"未知命令: {topic}")
        return

    # 分类展示
    categories = {
        "数据管理": ["scan", "export", "list-exports", "build-rag", "check-rag"],
        "系统运维": ["status", "health", "monitor-snap", "report", "config-info"],
        "维护操作": ["clear-cache", "clean-logs", "backup", "test"],
    }

    table = Table(title="可用命令", box=box.ROUNDED, border_style="cyan",
                  title_style="bold white")
    table.add_column("分类", style="dim")
    table.add_column("命令", style="bold cyan")
    table.add_column("说明", style="white")

    for cat, cmds in categories.items():
        first = True
        for c in cmds:
            if c in COMMANDS:
                _, desc = COMMANDS[c]
                table.add_row(cat if first else "", f"/{c}", desc)
                first = False

    console.print()
    console.print(table)
    console.print("  [dim]快捷键: s=status sc=scan e=export q=quit[/dim]")
    render_blank()


# ============================================================================
# 执行命令
# ============================================================================

def _execute_command(parsed: argparse.Namespace) -> int:
    """执行解析后的命令"""
    command = parsed.command

    if command == "quit":
        return -1  # 特殊返回码: 退出 REPL

    if command == "help":
        _show_help(getattr(parsed, "topic", ""))
        return 0

    from .cli_main import COMMANDS
    if command not in COMMANDS:
        render_error(f"未知命令: {command}")
        return 1

    func, description = COMMANDS[command]

    # 记录到会话
    args_dict = {k: v for k, v in vars(parsed).items()
                 if k != "command" and v is not None}
    session.record(command, args_dict)

    # 显示执行信息
    render_info(f"执行: [bold]{command}[/bold] — {description}")

    # 执行命令函数
    try:
        func(parsed)
        return 0
    except KeyboardInterrupt:
        render_warning("操作已中断")
        return 130
    except Exception as e:
        from .logger import get_logger
        logger = get_logger("repl")
        logger.exception(f"命令执行异常 [{command}]")
        render_error(str(e))
        return 1


# ============================================================================
# 自定义 prompt
# ============================================================================

def _get_prompt() -> Text:
    """生成 Claude Code 风格的提示符"""
    prompt = Text()
    prompt.append("\n  ", style="")
    prompt.append(">", style="bold cyan")
    prompt.append(" ", style="")
    return prompt


# ============================================================================
# REPL 主循环
# ============================================================================

def launch_repl(argv: Optional[List[str]] = None) -> int:
    """启动交互式 REPL"""
    import time
    from . import __version__
    from .logger import set_console_logging

    # REPL 模式下日志只写文件，避免和 Rich 输出混叠
    set_console_logging(False)

    session.started_at = time.time()

    _print_welcome()

    while True:
        try:
            user_input = console.input(_get_prompt())
        except (EOFError, KeyboardInterrupt):
            console.print("\n\n  [dim]会话结束。[/dim]")
            _save_history()
            set_console_logging(True)
            return 0

        user_input = user_input.strip()
        if not user_input:
            continue

        # 必须以 / 开头
        if not user_input.startswith("/"):
            render_warning("请使用斜杠命令，例如 [cyan]/status[/cyan] 或 [cyan]/help[/cyan]")
            continue

        parsed = _parse_slash_input(user_input)
        if parsed is None:
            continue

        result = _execute_command(parsed)
        if result == -1:  # quit
            console.print("\n  [dim]再见。[/dim]")
            _save_history()
            set_console_logging(True)
            return 0

        render_divider()

    return 0
