# 唐诗意象数据CLI运维管理系统 — 功能介绍与文件说明

> 本文档面向其他AI系统阅读，描述该CLI运维管理系统的功能架构、设计理念及每个文件的职责。代码位于 `cli_ops/` 目录，入口为 `cli_main.py`。

---

## 一、系统概述

### 1.1 定位

一个独立的命令行运维工具集，用于管理"唐诗意象智能分析系统"的诗歌JSON数据。提供15个CLI子命令、一个交互式REPL Shell、一个Web运维看板。

### 1.2 核心设计

```
                       人类用户                     AI Agent
                          │                            │
                   ┌──────┴──────┐            ┌───────┴───────┐
                   │  CLI 命令行  │            │  HTTP API调用   │
                   │  / REPL交互  │            │  (远程Hook)     │
                   └──────┬──────┘            └───────┬───────┘
                          │                            │
                   ┌──────┴────────────────────────────┴───────┐
                   │           CLI Operations Toolkit          │
                   │  cli_main.py (命令调度中心)                 │
                   └──────┬─────────────────────────────────────┘
         ┌────────────────┼────────────────┐
    ┌────┴────┐    ┌──────┴──────┐    ┌────┴────┐
    │ 数据管理 │    │   系统运维   │    │ 维护操作 │
    │ scan     │    │  status     │    │ backup   │
    │ export   │    │  health     │    │ clean-*  │
    │ build-rag│    │  monitor    │    │ test     │
    │ check-rag│    │  report     │    │          │
    └─────────┘    └─────────────┘    └─────────┘
```

### 1.3 双模式运行

| 模式 | 说明 |
|------|------|
| **命令行模式** | `python cli_main.py status --verbose` 执行单个命令后退出 |
| **REPL交互模式** | 无参数启动进入类Claude Code的交互Shell，支持`/命令`语法 |

### 1.4 技术栈

- **Python 3.10+**，纯标准库为主
- **Rich** — 终端渲染（Panel / Table / 彩色状态）
- **ChromaDB** — 向量数据库（可选）
- **Flask** — Web运维看板（可选，`cli_ops/web/app.py`）
- **psutil** — 系统资源监控（可选，降级可用）

---

## 二、15个CLI命令详解

### 2.1 数据管理类（5个）

| 命令 | 功能 | 关键参数 |
|------|------|---------|
| **scan** | 扫描数据目录，生成文件清单和摘要统计 | `--dir`, `--ext`, `--no-recursive` |
| **export** | 多格式数据导出：CSV/JSON/XML/TXT/HTML | `--format`, `--fields`, `--rows` |
| **list-exports** | 列出历史导出文件 | — |
| **check-rag** | 检查ChromaDB向量库状态 | — |
| **build-rag** | 构建/重建向量数据库 | `--force`, `--verbose` |

### 2.2 系统运维类（5个）

| 命令 | 功能 | 关键参数 |
|------|------|---------|
| **status** | 系统综合状态总览（7项目录+缓存+资源） | — |
| **health** | 8项健康检查（目录/权限/配置/依赖/磁盘） | — |
| **monitor-snap** | 采集系统监控快照（CPU/内存/磁盘/网络/进程） | — |
| **report** | 生成运维报告（text/json/html） | `--format` |
| **config-info** | 查看当前所有配置项 | — |

### 2.3 维护操作类（5个）

| 命令 | 功能 | 关键参数 |
|------|------|---------|
| **clear-cache** | 清除内存+文件双层缓存 | `--force` |
| **clean-logs** | 清理过期日志文件 | `--days` |
| **backup** | 备份数据目录 | `--output` |
| **test** | 运行单元测试（模块导入+功能断言） | `--verbose` |
| **help** | 显示帮助信息 | — |

---

## 三、每个文件的职责

### 3.1 入口层

| 文件 | 行数（去注释） | 职责 |
|------|:---:|------|
| `cli.py` | ~200 | **根目录独立入口**。提供 argparse 风格的旧版CLI（status/scan/export/check-rag等），与cli_main.py功能重叠但为独立实现，可直接 `python cli.py status` 运行 |
| `cli_main.py` | ~600 | **主入口 + 命令调度中心**。定义15个命令的完整实现，包含 `create_parser()` 参数解析和 `main()` 入口。无参数时自动启动REPL |

### 3.2 交互层

| 文件 | 行数 | 职责 |
|------|:---:|------|
| `repl.py` | ~280 | **REPL交互引擎**。实现类Claude Code的终端交互体验：`/`斜杠命令解析、readline历史记录和Tab补全、快捷键映射（s→status等）、命令别名（scan poems→--dir ./poem_json）、Rich渲染欢迎界面和帮助表格 |
| `session.py` | ~45 | **会话上下文**。REPL模式下维护跨命令的状态记忆：最后执行的命令、扫描目录、导出格式/路径、命令历史。支持链式操作"前一步做了什么→下一步基于此继续" |
| `rich_ui.py` | ~120 | **Rich终端渲染封装**。提供Panel标题、成功/错误/警告彩色输出、键值对表格、数据表格、状态徽章、进度条、分割线等渲染函数。REPL和所有命令共用 |

### 3.3 数据层

| 文件 | 行数 | 职责 |
|------|:---:|------|
| `models.py` | ~330 | **核心数据模型**。9个dataclass：FileInfo（文件元信息）、ScanResult（扫描结果+摘要）、ExportRecord（导出记录）、CacheEntry（缓存条目含TTL）、MonitorSnapshot（监控快照含CPU/内存/磁盘/网络/进程）、HealthStatus（健康状态+通过率）、BatchTask/BatchResult（批处理任务/结果）、SystemStatus（系统综合状态）。每个模型都有 `to_dict()` 序列化方法 |
| `config.py` | ~240 | **配置管理**。定义所有路径常量（DATA_DIR/EXPORT_DIR/LOG_DIR/CACHE_DIR等）、日志/缓存/导出/监控/扫描/批处理/健康检查的配置参数（共50+可配置项）、分类名称映射（7大类意象）、情感类别常量。包含ConfigManager类支持环境变量覆盖、运行时热更新、配置快照备份、变更历史追踪 |
| `persistence.py` | 无（在poem_lab中使用，CLI系统不直接依赖SQLite） | — |

### 3.4 处理层

| 文件 | 行数 | 职责 |
|------|:---:|------|
| `data_scanner.py` | ~230 | **数据目录扫描器**。递归扫描目录生成文件清单：文件元信息收集（路径/大小/修改时间/JSON有效性检测/行数）、按扩展名/大小/年龄分类统计、扫描结果摘要生成。包含ChangeDetector类：对比两次扫描结果检测文件增删改 |
| `export_engine.py` | ~400 | **多格式导出引擎**。支持5种格式导出：CSV（UTF-8-BOM编码，Excel兼容）、JSON（含metadata结构）、XML（pretty-print格式化）、TXT（TSV制表符分隔）、HTML（样式化表格报告）。特性：流式导出避免大文件OOM、字段过滤/重命名、行数限制、时间戳文件名、导出历史记录管理 |
| `preprocessor.py` | ~140 | **数据预处理**。JSON清洗（去除Markdown代码块包裹、修复常见格式错误如尾逗号/单引号/注释）、结构校验（验证必需顶层键"诗歌集"/"作者"/"标题"等）、安全解析（带错误收集的批量处理）、数据备份 |
| `batch_processor.py` | ~130 | **批量处理引擎**。ThreadPoolExecutor并发执行、可配置工作线程数/块大小/超时时间、单个任务超时控制、失败自动重试（可配置次数）、进度回调、结果汇总统计（完成/失败/超时数+成功率） |
| `cache_manager.py` | ~300 | **双层缓存系统**。MemoryCache：线程安全内存缓存，支持LRU/LFU/TTL淘汰策略，统计命中率/驱逐数/过期数，提供 `get_or_compute()` 缓存穿透保护。FileCache：JSON文件持久化缓存，MD5键名防冲突。`@cached`装饰器：自动缓存函数返回值。 |

### 3.5 监控层

| 文件 | 行数 | 职责 |
|------|:---:|------|
| `monitor.py` | ~280 | **系统资源监控**。采集5个维度：磁盘（shutil.disk_usage）、内存（psutil.virtual_memory+swap）、CPU（psutil.cpu_percent+核心数+频率）、网络（字节收发/包统计/活跃连接）、进程（PID/内存RSS/运行时间/打开文件）。支持快照历史（可配置保留数）、阈值告警（磁盘/内存/CPU超阈值触发回调）、4维健康度评分（A/B/C/D等级）、后台定时采集（daemon线程） |
| `health_checker.py` | ~300 | **健康检查器**。8项检查：Python环境（版本≥3.9）、磁盘空间（<1GB严重/1-5GB警告）、配置有效性（参数范围校验）、数据目录（存在+可读+非空）、导出/日志/缓存目录（可读写验证）、向量数据库（可选组件）。CheckRegistry：注册表模式+拓扑排序依赖解析。支持带重试检查、文本报告生成、Web适配器 |

### 3.6 输出层

| 文件 | 行数 | 职责 |
|------|:---:|------|
| `report_generator.py` | ~220 | **运维报告生成器**。收集6类数据（系统信息/目录状态/资源使用/健康检查/缓存统计/导出文件），生成3种格式：纯文本报告（ASCII框线+层级排版）、JSON报告（结构化数据）、HTML报告（样式化表格+颜色状态标记）。按时间戳保存到reports/目录 |
| `logger.py` | ~100 | **日志系统**。基于Python logging + RotatingFileHandler自动轮转（10MB/文件，保留10个备份）。支持控制台开关（REPL模式下关控制台避免与Rich输出混叠）、Logger实例缓存、LoggerMixin混入类、结构化日志辅助函数 |

### 3.7 基础层

| 文件 | 行数 | 职责 |
|------|:---:|------|
| `errors.py` | ~100 | **分层异常体系**。30+错误码（通用1000-1099/数据2000-2099/IO 3000-3099/网络4000-4099/导出5000-5099/批处理6000-6099）。每种异常关联HTTP状态码。支持异常序列化（to_dict）、批量错误聚合（ErrorCollector） |
| `utils.py` | ~180 | **通用工具函数集**。30+函数：字符串（truncate/slugify/remove_whitespace）、中文检测（is_chinese_char/chinese_ratio）、文件（format_file_size/ensure_dir/safe_filename）、数据（flatten_dict/deep_merge）、编码（safe_encode/to_json_bytes）、列表（chunk_list/unique_preserve_order/frequency_count）、哈希（file_md5/quick_hash） |
| `validators.py` | ~130 | **输入校验**。提供non_empty/length/range/regex_match/valid_path/valid_dir/valid_json/is_chinese/decimal_number等校验器。统一返回 `(bool, str)` 元组。ValidatedNamespace支持批量校验和错误收集 |
| `__init__.py` | ~40 | **包声明**。定义 `__version__ = "1.0.0"` 和 `__all__` 导出列表 |

### 3.8 Web前端（可选）

| 文件 | 行数 | 职责 |
|------|:---:|------|
| `web/app.py` | ~350 | **Flask Web运维看板**。提供：用户登录/注册（SHA256哈希）、主页Dashboard（统计数据卡片+图表数据）、操作日志展示、三层级REST API（status级系统状态API、session级会话管理API、auth级认证API）。设计为人类可读+AI Agent可调用双模式 |
| `web/templates/*.html` | 5个文件 | 登录/注册/主页/Dashboard页面，纯HTML+CSS无JS框架 |

---

## 四、架构总览图

```
cli_main.py ──┬── status       ──┬── config          (路径+缓存+系统资源)
              │                  ├── cache_manager   (双层缓存统计)
              │                  └── monitor         (CPU/内存/磁盘/进程)
              │
              ├── scan         ─── data_scanner      (扫描+分类+变更检测)
              │
              ├── export       ─── export_engine     (CSV/JSON/XML/TXT/HTML)
              │                  └── preprocessor    (JSON清洗+数据提取)
              │
              ├── health       ─── health_checker    (8项检查+评分+建议)
              │
              ├── report       ─── report_generator  (text/json/html)
              │                  └── 汇总 config+health+monitor+cache
              │
              ├── test         ─── 所有模块导入检测 + utils函数断言
              │
              ├── monitor-snap ── monitor            (快照+历史+告警)
              ├── check-rag    ── chromadb           (向量库状态查询)
              ├── build-rag    ── chromadb + preprocessor (构建向量库)
              ├── clean-logs   ── logger             (轮转日志清理)
              ├── backup       ── preprocessor       (数据备份)
              ├── clear-cache  ── cache_manager      (双层清除)
              ├── config-info  ── config             (63项配置列表)
              ├── list-exports ── export_engine      (导出历史)
              └── help         ── 自身docstring

repl.py ──── 调用 cli_main.COMMANDS ── 所有命令
              ├── readline     (历史+补全)
              ├── rich_ui      (渲染)
              └── session      (状态记忆)

web/app.py ── Flask ── 调用 health_checker / cache_manager / cli_main
              └── 为agent提供HTTP API远程操控入口
```

---

## 五、关键设计决策（给其他AI看）

1. **命令函数签名统一**：所有 `cmd_*` 函数接受 `argparse.Namespace` 参数，REPL和CLI模式复用同一函数
2. **Rich双模式**：通过 `RICH_MODE` 全局标志控制，REPL下用Rich渲染，CLI模式下用 `print()`，避免输出混叠
3. **psutil可选降级**：`HAS_PSUTIL` 标志控制，未安装时监控功能返回基础信息而非崩溃
4. **缓存键MD5**：FileCache用MD5哈希键名防止文件系统非法字符
5. **导出BOM头**：CSV文件手动写入 `﻿` 确保Excel正确识别中文
6. **配置优先级**：运行时覆盖 > 环境变量 > 模块常量 > 默认值
7. **错误码分段**：1000-通用、2000-数据、3000-IO、4000-网络、5000-导出、6000-批处理，方便AI Agent根据错误码决策
8. **批处理自动重试**：单个任务失败后按配置次数自动重试，避免整个批次因偶发错误中断
