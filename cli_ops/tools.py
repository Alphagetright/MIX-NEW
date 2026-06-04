# -*- coding: utf-8 -*-
"""
Tool Registry — 工具注册与动态调度
====================================

将 15 个 CLI 命令升级为 LLM 可发现、可调用的工具（function-calling 兼容）。

设计目标：
  - 每个命令暴露 name / description / parameters JSON Schema
  - 支持工具发现（list_for_llm）和执行（execute）
  - 输出捕获：将 stdout 重定向为字符串，供 Agent Loop 消费
  - 零破坏性：不修改现有 cmd_* 函数

使用方式：
    from cli_ops.tools import registry
    tools = registry.list_for_llm()       # → LLM 可用的工具列表
    result = registry.execute("status")   # → {"ok": True, "output": "...", "data": {...}}
"""

import io
import sys
import os
import argparse
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# ============================================================================
# Tool 数据类
# ============================================================================


class DangerLevel:
    """工具危险等级"""
    SAFE = "safe"           # 只读操作，随时可执行
    WRITE = "write"         # 写入操作（导出、报告）
    DESTRUCTIVE = "destructive"  # 破坏性操作（清缓存、重建RAG、清理日志、备份）


@dataclass
class Tool:
    """
    一个可被 LLM 发现和调用的工具

    Attributes:
        name: 工具名（与 CLI 命令一致）
        description: 功能描述
        parameters: JSON Schema 格式的参数定义
        handler: 执行函数（cmd_*）
        category: 分类（数据管理/系统运维/维护操作）
        danger_level: 危险等级（safe/write/destructive）
        requires_confirmation: 是否需要用户确认才能执行
    """
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    category: str = ""
    danger_level: str = DangerLevel.SAFE
    requires_confirmation: bool = False


# ============================================================================
# 工具执行结果
# ============================================================================


@dataclass
class ToolResult:
    """工具执行结果"""
    ok: bool
    tool_name: str
    output: str           # 捕获的 stdout 文本
    data: Any = None      # 结构化数据（如有）
    error: str = ""
    duration_ms: float = 0.0


# ============================================================================
# 辅助：dict → argparse.Namespace
# ============================================================================


# 缓存 parser 默认值，避免每次创建
_PARSER_DEFAULTS: Optional[argparse.Namespace] = None


def _get_parser_defaults() -> argparse.Namespace:
    """获取 parser 的默认 Namespace（含所有参数默认值）"""
    global _PARSER_DEFAULTS
    if _PARSER_DEFAULTS is None:
        from .cli_main import create_parser
        parser = create_parser()
        _PARSER_DEFAULTS = parser.parse_args([])
    return _PARSER_DEFAULTS


def _dict_to_namespace(d: dict) -> argparse.Namespace:
    """
    将参数字典转为 argparse.Namespace（兼容现有 cmd_* 函数）。
    以 parser 默认值为底，用户传入的参数覆盖默认值。
    这确保所有 argparse 定义的属性都存在，避免 AttributeError。
    """
    import copy
    defaults = _get_parser_defaults()
    ns = copy.copy(defaults)
    for k, v in (d or {}).items():
        setattr(ns, k, v)
    return ns


# ============================================================================
# 工具执行适配器：捕获 stdout
# ============================================================================


def _capture_output(func: Callable, args_dict: dict) -> ToolResult:
    """
    执行命令函数并捕获其 stdout 输出。

    参数:
        func: cmd_* 命令函数
        args_dict: 参数字典

    返回:
        ToolResult: 包含输出文本和结构化数据
    """
    start = time.time()
    ns = _dict_to_namespace(args_dict)
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf

    try:
        func(ns)
        output = buf.getvalue()
        return ToolResult(
            ok=True,
            tool_name=func.__name__,
            output=output,
            duration_ms=round((time.time() - start) * 1000, 1),
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            tool_name=func.__name__,
            output=buf.getvalue(),
            error=str(e),
            duration_ms=round((time.time() - start) * 1000, 1),
        )
    finally:
        sys.stdout = old_stdout


# ============================================================================
# Tool Registry
# ============================================================================


class ToolRegistry:
    """
    工具注册表 — 单例模式

    管理所有可被 LLM 调用的工具。支持：
      - 注册/注销工具
      - 列表查询（LLM function-calling 格式）
      - 按名称执行
      - 按分类过滤
      - 危险操作确认回调
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._confirm_callback: Optional[Callable[[Tool, dict], bool]] = None

    # ── 确认回调 ──

    def set_confirm_callback(self, callback: Callable[[Tool, dict], bool]) -> None:
        """
        设置危险操作确认回调。

        回调签名: callback(tool: Tool, args: dict) -> bool
        返回 True 表示用户确认，False 表示拒绝。

        用于 Agent Loop 在执行 destructive 操作前请求用户许可。
        """
        self._confirm_callback = callback

    @property
    def has_confirm_callback(self) -> bool:
        return self._confirm_callback is not None

    # ── 注册 ──

    def register(self, tool: Tool) -> None:
        """注册一个工具"""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> bool:
        """注销一个工具"""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    # ── 查询 ──

    def get(self, name: str) -> Optional[Tool]:
        """按名称获取工具"""
        return self._tools.get(name)

    def list_all(self) -> List[Tool]:
        """列出所有已注册工具"""
        return list(self._tools.values())

    def list_by_category(self) -> Dict[str, List[Tool]]:
        """按分类列出工具"""
        cats: Dict[str, List[Tool]] = {}
        for tool in self._tools.values():
            cats.setdefault(tool.category, []).append(tool)
        return cats

    def list_names(self) -> List[str]:
        """列出所有工具名"""
        return sorted(self._tools.keys())

    # ── LLM function-calling 格式 ──

    def list_for_llm(self) -> List[Dict[str, Any]]:
        """
        生成 OpenAI/Anthropic function-calling 兼容的工具列表。

        返回格式:
        [
            {
                "type": "function",
                "function": {
                    "name": "status",
                    "description": "Show comprehensive system status overview",
                    "parameters": { "type": "object", "properties": {...}, "required": [...] }
                }
            },
            ...
        ]
        """
        tools = []
        for tool in self._tools.values():
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            })
        return tools

    def list_for_prompt(self) -> str:
        """生成纯文本工具列表（用于 prompt-based function calling）"""
        lines = ["## Available Tools\n"]
        for tool in self._tools.values():
            params_desc = ""
            props = tool.parameters.get("properties", {})
            if props:
                param_parts = []
                for pname, pinfo in props.items():
                    req = "required" if pname in tool.parameters.get("required", []) else "optional"
                    param_parts.append(f"{pname} ({pinfo.get('type', 'str')}, {req}): {pinfo.get('description', '')}")
                params_desc = "\n    ".join(param_parts)
            lines.append(f"- **{tool.name}**: {tool.description}")
            if params_desc:
                lines.append(f"    {params_desc}")
            lines.append("")
        return "\n".join(lines)

    # ── 执行 ──

    def execute(self, name: str, args: Optional[Dict[str, Any]] = None,
                skip_confirm: bool = False) -> ToolResult:
        """
        按名称执行工具。

        参数:
            name: 工具名
            args: 参数字典
            skip_confirm: 跳过确认检查（用于非交互模式）

        返回:
            ToolResult: 执行结果
        """
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(
                ok=False,
                tool_name=name,
                output="",
                error=f"Unknown tool: {name}. Available: {', '.join(self.list_names())}",
            )

        # 危险操作确认检查
        if (not skip_confirm
                and tool.danger_level == DangerLevel.DESTRUCTIVE
                and self._confirm_callback):
            approved = self._confirm_callback(tool, args or {})
            if not approved:
                return ToolResult(
                    ok=False,
                    tool_name=name,
                    output="",
                    error=f"User declined confirmation for destructive operation: {name}",
                )

        return _capture_output(tool.handler, args or {})

    def is_safe(self, name: str) -> bool:
        """检查工具是否为只读操作"""
        tool = self._tools.get(name)
        return tool is not None and tool.danger_level == DangerLevel.SAFE

    def get_danger_level(self, name: str) -> Optional[str]:
        """获取工具的危险等级"""
        tool = self._tools.get(name)
        return tool.danger_level if tool else None


# ============================================================================
# 全局单例
# ============================================================================

registry = ToolRegistry()


# ============================================================================
# 注册所有 CLI 命令为工具
# ============================================================================


def _register_all_tools() -> None:
    """将 cli_main.py 中的所有命令注册为工具"""
    # 延迟导入避免循环依赖
    from .cli_main import (
        cmd_status, cmd_scan, cmd_export, cmd_clear_cache,
        cmd_list_exports, cmd_check_rag, cmd_build_rag,
        cmd_test, cmd_health, cmd_report, cmd_monitor_snap,
        cmd_clean_logs, cmd_backup, cmd_config_info,
    )

    # ── 数据管理类 ──

    registry.register(Tool(
        name="scan",
        description="扫描数据目录，生成文件清单。返回文件数、大小、扩展名分布、错误列表。",
        parameters={
            "type": "object",
            "properties": {
                "dir": {
                    "type": "string",
                    "description": "要扫描的目标目录路径，默认为 DATA_DIR（poem_json/）",
                },
                "ext": {
                    "type": "string",
                    "description": "扩展名过滤，逗号分隔，如 '.json,.txt'",
                },
                "no_recursive": {
                    "type": "boolean",
                    "description": "设为 true 禁用递归扫描",
                },
                "quiet": {
                    "type": "boolean",
                    "description": "安静模式，减少输出",
                },
            },
            "required": [],
        },
        handler=cmd_scan,
        category="数据管理",
        danger_level=DangerLevel.SAFE,
    ))

    registry.register(Tool(
        name="export",
        description="多格式数据导出：csv/json/xml/txt/html。将诗句分析数据导出为指定格式文件。",
        parameters={
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["csv", "json", "xml", "txt", "html"],
                    "description": "导出格式",
                },
                "prefix": {
                    "type": "string",
                    "description": "导出文件名前缀，默认 'export_{format}'",
                },
                "fields": {
                    "type": "string",
                    "description": "要导出的字段，逗号分隔，如 '标题,作者,意象文本'",
                },
                "rows": {
                    "type": "integer",
                    "description": "最大导出行数，默认 1000",
                },
            },
            "required": ["format"],
        },
        handler=cmd_export,
        category="数据管理",
        danger_level=DangerLevel.WRITE,
    ))

    registry.register(Tool(
        name="list-exports",
        description="列出所有历史导出文件及其大小、格式、修改时间。",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=cmd_list_exports,
        category="数据管理",
        danger_level=DangerLevel.SAFE,
    ))

    registry.register(Tool(
        name="check-rag",
        description="检查 ChromaDB 向量数据库状态：集合数、记录数、存储大小。",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=cmd_check_rag,
        category="数据管理",
        danger_level=DangerLevel.SAFE,
    ))

    registry.register(Tool(
        name="build-rag",
        description="构建或重建 ChromaDB 向量数据库。从数据目录加载所有 JSON 并创建向量索引。需要确认。",
        parameters={
            "type": "object",
            "properties": {
                "force": {
                    "type": "boolean",
                    "description": "跳过确认提示，直接重建。警告：会清除现有向量库！",
                },
                "verbose": {
                    "type": "boolean",
                    "description": "详细输出模式，显示每个文件的处理进度",
                },
            },
            "required": [],
        },
        handler=cmd_build_rag,
        category="数据管理",
        danger_level=DangerLevel.DESTRUCTIVE,
    ))

    # ── 系统运维类（全部只读） ──

    registry.register(Tool(
        name="status",
        description="系统综合状态总览：版本、目录状态、缓存命中率、磁盘/内存/CPU 使用率、最近导出列表。",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=cmd_status,
        category="系统运维",
        danger_level=DangerLevel.SAFE,
    ))

    registry.register(Tool(
        name="health",
        description="系统健康检查：数据目录、导出目录、日志、缓存、磁盘空间、Python 环境、配置有效性、RAG 状态。返回通过/失败详情和修复建议。",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=cmd_health,
        category="系统运维",
        danger_level=DangerLevel.SAFE,
    ))

    registry.register(Tool(
        name="monitor-snap",
        description="采集系统监控快照：CPU、内存、磁盘使用率及历史趋势（最近5条）。",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=cmd_monitor_snap,
        category="系统运维",
        danger_level=DangerLevel.SAFE,
    ))

    registry.register(Tool(
        name="report",
        description="生成运维报告（text/json/html格式），包含系统状态、健康检查、资源使用等综合信息。",
        parameters={
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["text", "json", "html"],
                    "description": "报告格式，默认 text",
                },
            },
            "required": [],
        },
        handler=cmd_report,
        category="系统运维",
        danger_level=DangerLevel.WRITE,
    ))

    registry.register(Tool(
        name="config-info",
        description="查看当前所有系统配置项及值。",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=cmd_config_info,
        category="系统运维",
        danger_level=DangerLevel.SAFE,
    ))

    # ── 维护操作类（全部需要确认） ──

    registry.register(Tool(
        name="clear-cache",
        description="清理所有系统缓存（内存缓存 + 文件缓存）。需要确认。",
        parameters={
            "type": "object",
            "properties": {
                "force": {
                    "type": "boolean",
                    "description": "跳过确认提示，直接清除。警告：不可逆操作！",
                },
            },
            "required": [],
        },
        handler=cmd_clear_cache,
        category="维护操作",
        danger_level=DangerLevel.DESTRUCTIVE,
    ))

    registry.register(Tool(
        name="test",
        description="运行单元测试：检查所有模块导入、核心工具函数正确性。返回通过/失败统计。",
        parameters={
            "type": "object",
            "properties": {
                "verbose": {
                    "type": "boolean",
                    "description": "详细输出模式，显示每个测试的结果",
                },
            },
            "required": [],
        },
        handler=cmd_test,
        category="维护操作",
        danger_level=DangerLevel.SAFE,
    ))

    registry.register(Tool(
        name="clean-logs",
        description="清理过期日志文件。默认保留最近 30 天的日志。需要确认。",
        parameters={
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "保留最近 N 天的日志，默认 30",
                },
            },
            "required": [],
        },
        handler=cmd_clean_logs,
        category="维护操作",
        danger_level=DangerLevel.DESTRUCTIVE,
    ))

    registry.register(Tool(
        name="backup",
        description="备份数据目录到指定位置。",
        parameters={
            "type": "object",
            "properties": {
                "output": {
                    "type": "string",
                    "description": "备份目标路径，默认为 backups/ 目录",
                },
            },
            "required": [],
        },
        handler=cmd_backup,
        category="维护操作",
        danger_level=DangerLevel.DESTRUCTIVE,
    ))


# 模块加载时自动注册
_register_all_tools()
