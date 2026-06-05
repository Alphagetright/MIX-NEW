# -*- coding: utf-8 -*-
"""
Rich 终端渲染封装
=================
为 REPL 模式提供美观的终端输出：Panel、Table、彩色状态行、进度条。
"""

from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()


# ============================================================================
# 基础渲染
# ============================================================================

def render_header(title: str, subtitle: str = "") -> None:
    """渲染标题面板"""
    content = Text(title, style="bold white")
    if subtitle:
        content.append(f"\n{subtitle}", style="dim")
    console.print(Panel(content, border_style="cyan", box=box.ROUNDED))


def render_success(msg: str) -> None:
    console.print(f"  [green]OK[/green]  {msg}")


def render_error(msg: str) -> None:
    console.print(f"  [red]ERR[/red] {msg}")


def render_warning(msg: str) -> None:
    console.print(f"  [yellow]WARN[/yellow] {msg}")


def render_info(msg: str) -> None:
    console.print(f"  [dim]>>>[/dim] {msg}")


# ============================================================================
# 键值对
# ============================================================================

def render_kv(key: str, value: Any, key_width: int = 22) -> None:
    console.print(f"  [dim]{key:{key_width}}[/dim] : [bold]{value}[/bold]")


def render_kv_table(pairs: List[Tuple[str, Any]], title: str = "") -> Table:
    """渲染键值对表格"""
    table = Table(title=title, box=box.ROUNDED, border_style="blue",
                  title_style="bold white", show_header=False)
    table.add_column("Key", style="dim", width=24)
    table.add_column("Value", style="bold")
    for key, value in pairs:
        table.add_row(key, str(value))
    console.print(table)
    return table


# ============================================================================
# 数据表格
# ============================================================================

def render_table(headers: List[str], rows: List[List[Any]],
                 title: str = "", caption: str = "") -> None:
    """渲染数据表格"""
    table = Table(title=title, caption=caption, box=box.ROUNDED,
                  border_style="blue", title_style="bold white")
    for i, header in enumerate(headers):
        style = "bold cyan" if i == 0 else "bold"
        table.add_column(header, style=style, no_wrap=(i == 0))
    for row in rows:
        table.add_row(*[str(c) for c in row])
    console.print(table)


# ============================================================================
# 状态徽章
# ============================================================================

def render_badge(label: str, value: Any, color: str = "green") -> None:
    """渲染统计徽章"""
    console.print(f"  [{color}]{value}[/{color}]  [dim]{label}[/dim]")


def render_status_line(ok: bool, label: str, detail: str = "") -> None:
    """渲染状态行，带状态标记"""
    icon = "[green]OK[/green]" if ok else "[red]!![/red]"
    detail_text = f"  [dim]({detail})[/dim]" if detail else ""
    console.print(f"  {icon}  {label}{detail_text}")


# ============================================================================
# 进度条
# ============================================================================

def progress_bar(description: str = "处理中") -> Progress:
    """创建一个进度条上下文管理器"""
    return Progress(
        SpinnerColumn(),
        TextColumn(f"[progress.description]{description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    )


# ============================================================================
# 分割线 & 空白
# ============================================================================

def render_divider() -> None:
    console.print("[dim]" + "-" * 70 + "[/dim]")


def render_blank() -> None:
    console.print()
