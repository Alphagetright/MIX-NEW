# -*- coding: utf-8 -*-
"""
唐诗意象数据运维管理系统 — 命令行主入口
========================================

提供 15 个子命令的完整运维工具集：

  status        系统综合状态总览
  scan          扫描数据目录，生成文件清单
  export        多格式数据导出（csv/json/xml/txt/html）
  clear-cache   清理系统缓存（内存 + 文件）
  list-exports  列出历史导出文件
  check-rag     检查向量数据库状态
  build-rag     构建/重建向量数据库
  test          运行单元测试
  health        系统健康检查
  report        生成运维报告
  monitor-snap  采集系统监控快照
  clean-logs    清理过期日志
  backup        备份数据目录
  config-info   查看当前配置
  help          显示帮助信息

Usage:
    python cli_main.py <command> [options]

Examples:
    python cli_main.py status
    python cli_main.py scan --dir ./poem_json
    python cli_main.py export --format csv
    python cli_main.py health
    python cli_main.py report --format html
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Any, Dict, List, Optional

# 将包所在目录加入 Python 路径
_package_dir = os.path.dirname(os.path.abspath(__file__))
if _package_dir not in sys.path:
    sys.path.insert(0, _package_dir)

from .config import (
    DATA_DIR, EXPORT_DIR, LOG_DIR, CACHE_DIR, RAG_DB_DIR, REPORT_DIR, BACKUP_DIR,
)
from .logger import get_logger

logger = get_logger("cli_main")


# ============================================================================
# 渲染模式控制
# ============================================================================

RICH_MODE = False  # REPL 启动时设为 True，切换富文本输出


def _set_rich_mode(enabled: bool) -> None:
    global RICH_MODE
    RICH_MODE = enabled


# ============================================================================
# 辅助函数
# ============================================================================


def _print_header(title: str, width: int = 60) -> None:
    if RICH_MODE:
        from .rich_ui import render_header
        render_header(title)
        return
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def _print_kv(key: str, value: Any, indent: int = 2) -> None:
    if RICH_MODE:
        from .rich_ui import render_kv
        render_kv(key, value)
        return
    print(f"{' ' * indent}{key:25s}: {value}")


def _confirm_action(prompt: str) -> bool:
    """交互式确认操作"""
    try:
        resp = input(f"\n{prompt} [y/N]: ").strip().lower()
        return resp in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        return False


# ============================================================================
# 命令: status
# ============================================================================


def cmd_status(args) -> None:
    """显示系统综合状态总览"""
    _print_header("唐诗意象数据运维管理系统 — 系统状态")

    # 版本信息
    from . import __version__ as pkg_version
    print(f"  版本: {pkg_version}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 目录状态
    _print_header("目录状态")
    dirs = [
        ("数据目录", DATA_DIR),
        ("导出目录", EXPORT_DIR),
        ("日志目录", LOG_DIR),
        ("缓存目录", CACHE_DIR),
        ("向量库", RAG_DB_DIR),
        ("报告目录", REPORT_DIR),
        ("备份目录", BACKUP_DIR),
    ]
    for name, path in dirs:
        exists = os.path.exists(path)
        status = "存在" if exists else "缺失"
        if exists and os.path.isdir(path):
            file_count = len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
            total_size = sum(
                os.path.getsize(os.path.join(path, f))
                for f in os.listdir(path)
                if os.path.isfile(os.path.join(path, f))
            )
            from .utils import format_file_size
            status += f" | {file_count} 文件 | {format_file_size(total_size)}"
        _print_kv(name, status)

    # 缓存状态
    _print_header("缓存状态")
    from .cache_manager import get_all_cache_stats
    stats = get_all_cache_stats()
    mem = stats.get("memory", {})
    _print_kv("内存缓存条目", f"{mem.get('size', 0)}")
    _print_kv("内存命中率", f"{mem.get('hit_rate_pct', 0)}%")
    _print_kv("缓存启用", "是" if stats.get("global_enabled") else "否")
    file_c = stats.get("file", {})
    _print_kv("文件缓存条目", f"{file_c.get('size', 0)}")
    _print_kv("文件缓存大小", file_c.get("total_size_formatted", "N/A"))

    # 系统资源
    _print_header("系统资源")
    from .monitor import system_monitor
    snap = system_monitor.snapshot()
    disk = snap.get("disk", {})
    mem2 = snap.get("memory", {})
    cpu = snap.get("cpu", {})
    _print_kv("磁盘使用率", f"{disk.get('percent', '?')}%")
    _print_kv("磁盘可用", f"{disk.get('free_gb', '?')} GB")
    _print_kv("内存使用率", f"{mem2.get('percent', '?')}%")
    _print_kv("CPU 使用率", f"{cpu.get('percent', '?')}%")
    _print_kv("CPU 核心数", cpu.get("count", "?"))

    # 导出文件
    from .export_engine import list_exports
    exports = list_exports()
    print(f"\n  导出文件: {len(exports)} 个")
    for exp in exports[:5]:
        print(f"    {exp.file_name}  ({exp.format})")

    print()


# ============================================================================
# 命令: scan
# ============================================================================


def cmd_scan(args) -> None:
    """扫描数据目录"""
    directory = args.dir or DATA_DIR
    extensions = args.ext.split(",") if args.ext else None
    recursive = not args.no_recursive

    _print_header(f"数据目录扫描: {directory}")
    print(f"  扩展名过滤: {extensions or '默认 (.json, .txt, .csv, .tsv)'}")
    print(f"  递归扫描: {'是' if recursive else '否'}")
    print()

    from .data_scanner import scan_directory, get_scan_summary
    result = scan_directory(directory, extensions=extensions, recursive=recursive)

    summary = get_scan_summary(result)
    _print_kv("总文件数", summary["total_files"])
    _print_kv("总大小", summary["total_size_formatted"])
    _print_kv("扫描耗时", f"{summary['scan_time']} 秒")
    _print_kv("跳过文件", summary["skipped_count"])
    _print_kv("错误数", summary["error_count"])
    _print_kv("无效JSON", summary["invalid_json_count"])

    print("\n  按扩展名分布:")
    for ext, count in summary["by_extension"].items():
        print(f"    {ext or '无扩展名':15s}: {count:5d}")

    print("\n  按大小分布:")
    for cat, count in summary["by_size"].items():
        print(f"    {cat:10s}: {count:5d}")

    if not args.quiet and len(result.errors) > 0:
        print(f"\n  错误详情 (前10条):")
        for err in result.errors[:10]:
            print(f"    ! {err[:120]}")

    print()


# ============================================================================
# 命令: export
# ============================================================================


def cmd_export(args) -> None:
    """多格式数据导出"""
    fmt = args.format.lower()
    prefix = args.prefix or f"export_{fmt}"
    fields = args.fields.split(",") if args.fields else None
    rows = int(args.rows) if args.rows else 1000

    _print_header(f"数据导出: {fmt.upper()}")
    print(f"  格式: {fmt}")
    print(f"  文件名前缀: {prefix}")
    print(f"  行数限制: {rows}")
    if fields:
        print(f"  导出字段: {', '.join(fields)}")

    # 模拟数据（实际使用时从文件加载）
    sample_data = _load_sample_data(rows)

    if not sample_data:
        print("\n  错误: 没有可导出的数据。请检查数据目录配置。")
        return

    from .export_engine import export_data
    record = export_data(sample_data, fmt=fmt, filename_prefix=prefix, fields=fields)

    if record.status == "success":
        print(f"\n  导出成功!")
        _print_kv("文件路径", record.file_path)
        _print_kv("文件大小", f"{record.file_size / 1024:.1f} KB")
        _print_kv("导出行数", record.rows_exported)
        _print_kv("导出列数", record.columns_exported)
        _print_kv("耗时", f"{record.duration} 秒")
    else:
        print(f"\n  导出失败: {record.error_message}")

    print()


def _load_sample_data(max_rows: int = 1000) -> List[Dict[str, Any]]:
    """从数据目录加载样本数据"""
    rows = []
    if not os.path.exists(DATA_DIR):
        return rows

    import glob
    import re as regex
    from .preprocessor import clean_json_content

    json_files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    for fp in json_files[:5]:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read().strip()
            content, _ = clean_json_content(content)
            data = json.loads(content)
            poems = _extract_poems(data)
            for poem in poems:
                for unit in poem.get("分析单元", []):
                    if isinstance(unit, dict):
                        rows.append({
                            "诗歌编号": poem.get("诗歌编号", ""),
                            "标题": poem.get("标题", ""),
                            "作者": poem.get("作者", ""),
                            "体裁": poem.get("分类标签", ""),
                            "意象文本": unit.get("文本", ""),
                            "词性": unit.get("词性", ""),
                            "感知通道": unit.get("感知通道", ""),
                            "表现功能": unit.get("表现功能", ""),
                            "情感类别": unit.get("情感类别", ""),
                            "情感极性": unit.get("情感极性", ""),
                        })
                        if len(rows) >= max_rows:
                            return rows[:max_rows]
        except Exception as e:
            logger.warning(f"加载文件失败 [{fp}]: {e}")
    return rows[:max_rows]


def _extract_poems(node: Any) -> List[Dict]:
    """递归提取诗歌节点"""
    found = []
    if isinstance(node, dict):
        if "分析单元" in node:
            found.append(node)
        else:
            for v in node.values():
                found.extend(_extract_poems(v))
    elif isinstance(node, list):
        for item in node:
            found.extend(_extract_poems(item))
    return found


# ============================================================================
# 命令: clear-cache
# ============================================================================


def cmd_clear_cache(args) -> None:
    """清理系统缓存"""
    if not args.force:
        if not _confirm_action("确认清除所有缓存？"):
            print("  已取消。")
            return

    from .cache_manager import clear_all_caches
    result = clear_all_caches()
    _print_header("缓存清理完成")
    _print_kv("内存缓存清除", f"{result['memory_cleared']} 条")
    _print_kv("文件缓存清除", f"{result['file_cleared']} 个")
    print()


# ============================================================================
# 命令: list-exports
# ============================================================================


def cmd_list_exports(args) -> None:
    """列出历史导出文件"""
    from .export_engine import list_exports, get_export_stats
    exports = list_exports()
    stats = get_export_stats()

    _print_header("导出文件列表")
    _print_kv("导出目录", stats["export_directory"])
    _print_kv("总文件数", stats["total_files"])
    _print_kv("总大小", stats["total_size_formatted"])

    if exports:
        print(f"\n  {'文件名':35s} {'格式':8s} {'大小':>12s}  {'修改时间'}")
        print(f"  {'-'*80}")
        for exp in exports[:20]:
            print(f"  {exp.file_name:35s} {exp.format:8s} "
                  f"{exp.file_size / 1024:9.1f} KB  "
                  f"{datetime.fromtimestamp(exp.created_at).strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("\n  (无导出文件)")

    print()


# ============================================================================
# 命令: health
# ============================================================================


def cmd_health(args) -> None:
    """系统健康检查"""
    from .health_checker import run_health_check, print_health_report

    _print_header("系统健康检查")
    print("  正在执行健康检查...")
    status = run_health_check()
    print(print_health_report(status))
    print()


# ============================================================================
# 命令: report
# ============================================================================


def cmd_report(args) -> None:
    """生成运维报告"""
    fmt = args.format.lower()
    _print_header(f"生成运维报告: {fmt.upper()}")

    from .report_generator import save_report
    path = save_report(fmt=fmt)
    print(f"\n  报告已生成: {path}")
    print(f"  文件大小: {os.path.getsize(path) / 1024:.1f} KB")
    print()


# ============================================================================
# 命令: check-rag
# ============================================================================


def cmd_check_rag(args) -> None:
    """检查向量数据库状态"""
    _print_header("向量数据库状态检查")

    if not os.path.exists(RAG_DB_DIR):
        print("  向量数据库目录不存在。")
        print(f"  路径: {RAG_DB_DIR}")
        print("  提示: 运行 'python cli_main.py build-rag' 构建向量库。")
        return

    file_count = len([
        f for f in os.listdir(RAG_DB_DIR)
        if os.path.isfile(os.path.join(RAG_DB_DIR, f))
    ])
    total_size = sum(
        os.path.getsize(os.path.join(RAG_DB_DIR, f))
        for f in os.listdir(RAG_DB_DIR)
        if os.path.isfile(os.path.join(RAG_DB_DIR, f))
    )
    from .utils import format_file_size
    _print_kv("向量库路径", RAG_DB_DIR)
    _print_kv("文件数", file_count)
    _print_kv("总大小", format_file_size(total_size))

    try:
        import chromadb
        client = chromadb.PersistentClient(path=RAG_DB_DIR)
        collections = client.list_collections()
        print(f"\n  向量集合: {len(collections)} 个")
        for col in collections:
            print(f"    - {col.name}: {col.count()} 条记录")
    except ImportError:
        print("\n  ChromaDB 未安装。运行: pip install chromadb")
    except Exception as e:
        print(f"\n  向量库访问异常: {e}")

    print()


# ============================================================================
# 命令: build-rag
# ============================================================================


def cmd_build_rag(args) -> None:
    """构建向量数据库"""
    _print_header("构建向量数据库")

    if not os.path.exists(DATA_DIR):
        print(f"  错误: 数据目录不存在: {DATA_DIR}")
        return

    if not args.force:
        if not _confirm_action("将重建向量数据库（现有数据将清除），继续？"):
            print("  已取消。")
            return

    print("  正在扫描数据文件...")
    import glob
    from .preprocessor import safe_parse_json

    json_files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    print(f"  找到 {len(json_files)} 个 JSON 文件")

    poems = []
    for fp in json_files:
        data, errors = safe_parse_json(fp)
        if data:
            found = _extract_poems(data)
            poems.extend(found)
            if args.verbose:
                print(f"    {os.path.basename(fp)}: {len(found)} 首诗歌")

    print(f"\n  共解析 {len(poems)} 首诗歌")

    # 检查 ChromaDB
    try:
        import chromadb
        import shutil
        if os.path.exists(RAG_DB_DIR):
            shutil.rmtree(RAG_DB_DIR)
        os.makedirs(RAG_DB_DIR, exist_ok=True)

        client = chromadb.PersistentClient(path=RAG_DB_DIR)
        # 根据需求决定是否实际嵌入
        print(f"  向量库已初始化: {RAG_DB_DIR}")
        print(f"  注意: 实际向量嵌入需要安装并配置嵌入模型。")
        print(f"  当前已准备好 ChromaDB 环境。")
    except ImportError:
        print("  警告: ChromaDB 未安装，无法构建向量库。")
        print("  安装: pip install chromadb")

    print()


# ============================================================================
# 命令: monitor-snap
# ============================================================================


def cmd_monitor_snap(args) -> None:
    """采集系统监控快照"""
    from .monitor import system_monitor
    snap = system_monitor.collect()

    _print_header("系统监控快照")
    print(f"  采集时间: {snap['timestamp_formatted']}")

    disk = snap["disk"]
    print(f"\n  磁盘: {disk['percent']}% 使用 | "
          f"可用 {disk['free_gb']}GB / 总量 {disk['total_gb']}GB")

    mem = snap["memory"]
    print(f"  内存: {mem.get('percent', '?')}% 使用 | "
          f"可用 {mem.get('available_gb', '?')}GB / 总量 {mem.get('total_gb', '?')}GB")

    cpu = snap["cpu"]
    print(f"  CPU:  {cpu.get('percent', '?')}% 使用 | {cpu.get('count', '?')} 核心")

    proc = snap["process"]
    print(f"\n  进程 PID: {proc['pid']} | Python {proc['python_version']}")
    print(f"  运行时间: {proc['uptime_seconds']} 秒")
    print(f"  内存 RSS: {proc.get('memory_rss_mb', '?')} MB")

    history = system_monitor.get_history(5)
    print(f"\n  历史快照: {len(history)} 条 (最新5条):")
    for h in history[:5]:
        print(f"    {h['timestamp_formatted']}  "
              f"CPU={h.get('cpu',{}).get('percent','?')}%  "
              f"Mem={h.get('memory',{}).get('percent','?')}%  "
              f"Disk={h.get('disk',{}).get('percent','?')}%")
    print()


# ============================================================================
# 命令: clean-logs
# ============================================================================


def cmd_clean_logs(args) -> None:
    """清理过期日志文件"""
    days = int(args.days) if args.days else 30
    _print_header(f"清理日志: 保留最近 {days} 天")

    from .logger import clean_old_logs, get_log_stats
    before = get_log_stats()
    deleted = clean_old_logs(keep_days=days)
    after = get_log_stats()

    print(f"  删除: {deleted} 个文件")
    print(f"  剩余: {after['total_files']} 个文件")
    print(f"  节省: {(before['total_size_bytes'] - after['total_size_bytes']) / 1024:.1f} KB")
    print()


# ============================================================================
# 命令: backup
# ============================================================================


def cmd_backup(args) -> None:
    """备份数据目录"""
    _print_header("数据备份")
    from .preprocessor import backup_data
    dest = backup_data(DATA_DIR, args.output)
    print(f"  数据已备份到: {dest}")
    file_count = len([f for f in os.listdir(dest) if os.path.isfile(os.path.join(dest, f))])
    total_size = sum(os.path.getsize(os.path.join(dest, f))
                     for f in os.listdir(dest) if os.path.isfile(os.path.join(dest, f)))
    from .utils import format_file_size
    print(f"  备份文件数: {file_count}")
    print(f"  备份大小: {format_file_size(total_size)}")
    print()


# ============================================================================
# 命令: config-info
# ============================================================================


def cmd_config_info(args) -> None:
    """查看当前配置"""
    from .config import config_manager
    _print_header("当前系统配置")
    configs = config_manager.list_all()
    for key, val in configs.items():
        _print_kv(key, str(val)[:80])
    print()


# ============================================================================
# 命令: test
# ============================================================================


def cmd_test(args) -> None:
    """运行单元测试"""
    _print_header("运行单元测试")

    test_count = 0
    passed = 0
    failed = 0

    # 基础模块导入测试
    modules_to_test = [
        "config", "errors", "logger", "utils", "validators",
        "models", "cache_manager", "monitor", "export_engine",
        "preprocessor", "data_scanner", "health_checker",
        "report_generator", "batch_processor",
    ]

    for mod_name in modules_to_test:
        try:
            __import__(f"cli_ops.{mod_name}")
            passed += 1
            if args.verbose:
                print(f"  PASS  {mod_name}")
        except ImportError as e:
            failed += 1
            print(f"  FAIL  {mod_name}: {e}")
        test_count += 1

    # 功能测试
    from .utils import truncate, is_chinese_char, frequency_count, format_file_size
    assert truncate("hello world", 8) == "hello..."
    assert is_chinese_char("唐")
    assert frequency_count(["a", "b", "a", "c", "b", "a"])[0] == ("a", 3)
    assert "KB" in format_file_size(2048)
    passed += 4
    test_count += 4

    print(f"\n  测试结果: {passed}/{test_count} 通过, {failed} 失败")
    if failed == 0:
        print("  状态: ALL TESTS PASSED")
    print()


# ============================================================================
# 命令: help
# ============================================================================


def cmd_help(args) -> None:
    """显示帮助信息"""
    print(__doc__)


# ============================================================================
# 主入口
# ============================================================================


COMMANDS = {
    "status": (cmd_status, "系统综合状态总览"),
    "scan": (cmd_scan, "扫描数据目录并生成文件清单"),
    "export": (cmd_export, "多格式数据导出 (csv/json/xml/txt/html)"),
    "clear-cache": (cmd_clear_cache, "清理系统缓存"),
    "list-exports": (cmd_list_exports, "列出历史导出文件"),
    "check-rag": (cmd_check_rag, "检查向量数据库状态"),
    "build-rag": (cmd_build_rag, "构建/重建向量数据库"),
    "test": (cmd_test, "运行单元测试"),
    "health": (cmd_health, "系统健康检查"),
    "report": (cmd_report, "生成运维报告 (text/json/html)"),
    "monitor-snap": (cmd_monitor_snap, "采集系统监控快照"),
    "clean-logs": (cmd_clean_logs, "清理过期日志文件"),
    "backup": (cmd_backup, "备份数据目录"),
    "config-info": (cmd_config_info, "查看当前系统配置"),
    "help": (cmd_help, "显示此帮助信息"),
}


def create_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="tang-cli-ops",
        description="唐诗意象数据运维管理系统 — 命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例: python cli_main.py status"
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="help",
        choices=list(COMMANDS.keys()),
        help="要执行的命令",
    )

    parser.add_argument("--dir", "-d", help="目标目录路径")
    parser.add_argument("--format", "-f", default="csv", help="导出/报告格式")
    parser.add_argument("--prefix", help="导出文件名前缀")
    parser.add_argument("--fields", help="导出字段（逗号分隔）")
    parser.add_argument("--rows", default=1000, help="最大导出行数")
    parser.add_argument("--ext", help="扫描扩展名过滤（逗号分隔）")
    parser.add_argument("--no-recursive", action="store_true", help="禁用递归扫描")
    parser.add_argument("--days", default=30, help="日志保留天数")
    parser.add_argument("--output", "-o", help="输出/备份路径")
    parser.add_argument("--force", "-y", action="store_true", help="跳过确认提示")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出模式")
    parser.add_argument("--quiet", "-q", action="store_true", help="安静模式（减少输出）")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI 主入口 — 无参数进入 REPL，有参数走传统 argparse 模式"""
    parser = create_parser()

    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        # 无参数 → 进入交互式 REPL
        from .repl import launch_repl
        _set_rich_mode(True)
        try:
            return launch_repl()
        finally:
            _set_rich_mode(False)

    args = parser.parse_args(argv)
    command = args.command

    if command not in COMMANDS:
        print(f"未知命令: {command}")
        print(f"有效命令: {', '.join(sorted(COMMANDS.keys()))}")
        return 1

    func, description = COMMANDS[command]
    logger.info(f"执行命令: {command} — {description}")

    try:
        func(args)
        return 0
    except KeyboardInterrupt:
        print("\n  操作已中断。")
        return 130
    except Exception as e:
        logger.exception(f"命令执行异常 [{command}]")
        print(f"\n  错误: {e}")
        if hasattr(args, 'verbose') and args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
