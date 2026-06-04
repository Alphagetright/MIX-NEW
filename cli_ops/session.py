# -*- coding: utf-8 -*-
"""
会话上下文管理
==============
REPL 模式下维护跨命令的会话状态，支持操作链式调用。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SessionContext:
    """REPL 会话上下文 — 记住"刚才做了什么"以便链式操作"""

    command_count: int = 0
    last_command: str = ""
    last_args: Dict[str, Any] = field(default_factory=dict)
    command_history: List[str] = field(default_factory=list)

    # 操作结果缓存
    last_scan_directory: str = ""
    last_scan_file_count: int = 0
    last_export_format: str = ""
    last_export_path: str = ""
    last_export_rows: int = 0
    last_health_status: str = ""

    started_at: float = 0.0

    def record(self, command: str, args: Dict[str, Any] = None) -> None:
        self.command_count += 1
        self.last_command = command
        self.last_args = args or {}
        self.command_history.append(command)
        if len(self.command_history) > 500:
            self.command_history = self.command_history[-500:]

    @property
    def is_first_command(self) -> bool:
        return self.command_count <= 1

    @property
    def uptime_commands(self) -> int:
        return self.command_count


# 全局会话实例
session = SessionContext()
