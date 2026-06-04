# -*- coding: utf-8 -*-
"""
唐诗意象数据运维管理系统 — CLI Operations Toolkit
==================================================
独立命令行运维工具，提供古典文学标注数据的管理、监控、导出、维护等功能。

功能模块：
  - cli_main         主命令行入口（15个子命令 + REPL交互模式）
  - repl             类Claude Code交互式REPL引擎
  - session          会话上下文管理（跨命令状态记忆）
  - rich_ui          Rich终端渲染封装
  - monitor          系统资源监控（CPU/内存/磁盘/网络/进程）
  - cache_manager    双层缓存管理（内存缓存 + 文件缓存 + TTL策略）
  - export_engine    多格式数据导出（CSV/JSON/XML/TXT/HTML报告）
  - data_scanner     数据目录扫描与完整性校验
  - health_checker   系统健康度检查与告警
  - report_generator 运维报告自动生成
  - batch_processor  批量数据处理与任务调度
  - preprocessor     数据清洗与格式转换
  - models           核心数据模型定义
  - config           配置管理与环境变量
  - logger           分级日志记录与轮转
  - errors           分层异常体系
  - utils            通用工具函数集
  - validators       输入校验与数据验证

版本：V1.0
作者：唐诗意象数据分析团队
开发完成日期：2026年5月
"""

__version__ = "1.0.0"
__author__ = "唐诗意象数据分析团队"
__all__ = [
    "cli_main",
    "repl",
    "session",
    "rich_ui",
    "monitor",
    "cache_manager",
    "export_engine",
    "data_scanner",
    "health_checker",
    "report_generator",
    "batch_processor",
    "preprocessor",
    "models",
    "config",
    "logger",
    "errors",
    "utils",
    "validators",
]
