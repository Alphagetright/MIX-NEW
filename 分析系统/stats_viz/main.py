# -*- coding: utf-8 -*-
"""
诗歌意象多维统计与可视化系统 — 主入口
======================================
提供命令行统计分析和数据导出功能。

Usage:
    python -m tang_stats_viz.main stats      # 输出全维度统计摘要
    python -m tang_stats_viz.main top50      # Top50 高频意象
    python -m tang_stats_viz.main category   # 分类域分布
    python -m tang_stats_viz.main emotion    # 情感分布
    python -m tang_stats_viz.main authors    # 诗人统计
    python -m tang_stats_viz.main export     # 导出统计结果
    python -m tang_stats_viz.main report     # 生成统计报告
    python -m tang_stats_viz.main test       # 运行自检
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Any, Dict, List

from .config import (
    DATA_DIR, EXPORT_DIR, TOP_IMAGES_N, PAGE_SIZE, CATEGORY_NAME_MAP,
    CATEGORY_MAJOR_MAP, DIMENSION_KEYS, EMOTION_LABELS,
)
from .logger import get_logger

logger = get_logger("main")


def print_header(title: str, width: int = 62) -> None:
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def print_kv(key: str, value: Any, indent: int = 2) -> None:
    print(f"{' ' * indent}{key:22s}: {value}")


# ─── 基础统计命令 ───

def cmd_stats(args) -> None:
    """输出全维度统计摘要"""
    from .data_loader import build_traceback_dataset, get_summary_stats
    from .stats_engine import StatsEngine

    print_header("诗歌意象多维统计与可视化系统 V1.0")
    summary = get_summary_stats()
    print(f"  数据目录: {DATA_DIR}")
    print(f"  净解析诗歌: {summary['total_poems']} 首")
    print(f"  提取意象条目: {summary['total_images']} 条")
    print(f"  已知诗人: {summary['total_authors']} 位")

    engine = StatsEngine()
    engine.load_data()
    report = engine.summary_report()

    print_header("基础统计")
    for k, v in report["基础统计"].items():
        print_kv(k, v)

    print_header(f"高频意象 Top10")
    for item in report["意象频次Top10"]:
        print(f"    {item['text']:20s}  {item['count']:5d}")

    print_header("分类域分布")
    for k, v in sorted(report["分类域分布"].items(), key=lambda x: x[1], reverse=True):
        print(f"    {k:20s}  {v:5d}")

    print_header("大类分布")
    for k, v in report["大类分布"].items():
        print(f"    {k:20s}  {v:5d}")

    print_header("情感分布")
    for k, v in sorted(report["情感类别分布"].items(), key=lambda x: x[1], reverse=True):
        print(f"    {k:20s}  {v:5d}")

    print()


def cmd_top50(args) -> None:
    """输出 Top50 高频意象"""
    from .stats_engine import StatsEngine
    engine = StatsEngine(); engine.load_data()
    data = engine.top_imagery(50)
    print_header("核心意象 Top50")
    for i, (text, count) in enumerate(data, 1):
        print(f"  {i:3d}. {text:20s}  {count:5d}")
    print()


def cmd_category(args) -> None:
    """输出分类域分布"""
    from .stats_engine import StatsEngine
    engine = StatsEngine(); engine.load_data()
    cat = engine.category_distribution()
    major = engine.major_category_distribution()
    print_header("意象分类域分布")
    for k, v in sorted(cat.items(), key=lambda x: x[1], reverse=True):
        print(f"  {k:20s}  {v:5d}")
    print_header("意象大类分布")
    for k, v in major.items():
        print(f"  {k:20s}  {v:5d}")
    print()


def cmd_emotion(args) -> None:
    """输出情感分布"""
    from .stats_engine import StatsEngine
    engine = StatsEngine(); engine.load_data()
    emo = engine.emotion_distribution()
    pol = engine.emotion_polarity_distribution()
    print_header("情感类别分布")
    for k, v in sorted(emo.items(), key=lambda x: x[1], reverse=True):
        print(f"  {k:20s}  {v:5d}")
    print_header("情感极性分布")
    for k, v in pol.items():
        print(f"  {k:20s}  {v:5d}")

    cross = engine.cross_analysis_emotion_category()
    print_header("情感 x 分类域 交叉分析")
    for emo_k, cats in sorted(cross.items())[:10]:
        print(f"  [{emo_k}]")
        for cat_k, cnt in sorted(cats.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {cat_k:20s}  {cnt:5d}")
    print()


def cmd_authors(args) -> None:
    """输出诗人统计"""
    from .stats_engine import StatsEngine
    engine = StatsEngine(); engine.load_data()
    stats = engine.author_statistics(25)
    print_header("诗人意象使用统计 Top25")
    for i, s in enumerate(stats, 1):
        print(f"  {i:2d}. {s['author']:15s}  总量:{s['total_imagery_uses']:5d}  去重:{s['unique_imagery']:4d}")
        print(f"      Top5: {', '.join(s['top5_imagery'][:5])}")
    print()


def cmd_export(args) -> None:
    """导出统计结果"""
    from .stats_engine import StatsEngine
    from .export_service import export_to_csv, export_to_json, export_stats_to_html

    fmt = args.format.lower()
    engine = StatsEngine(); engine.load_data()
    data = engine._data

    if fmt == "csv":
        record = export_to_csv(data, prefix="stats_export")
    elif fmt == "json":
        record = export_to_json(engine.summary_report(), prefix="stats_export")
    elif fmt == "html":
        record = export_stats_to_html(engine, prefix="stats_report")
    else:
        print(f"不支持的格式: {fmt}")
        return

    if record.status == "success":
        print(f"导出成功: {record.file_path} ({record.file_size / 1024:.1f} KB, {record.duration}s)")
    else:
        print(f"导出失败: {record.error_message}")


def cmd_report(args) -> None:
    """生成统计报告"""
    from .stats_engine import StatsEngine
    from .report_builder import save_report

    engine = StatsEngine(); engine.load_data()
    summary = engine.summary_report()
    fmt = args.format.lower() if args.format else "text"
    path = save_report(summary, fmt=fmt)
    print(f"报告已生成: {path} ({os.path.getsize(path) / 1024:.1f} KB)")


def cmd_test(args) -> None:
    """运行自检"""
    print_header("系统自检")

    modules = ["config", "errors", "logger", "utils", "validators",
               "models", "preprocessor", "data_loader", "stats_engine",
               "chart_data_builder", "export_service", "report_builder"]
    passed = 0
    failed = 0
    for mod in modules:
        try:
            __import__(f"tang_stats_viz.{mod}", fromlist=[mod])
            passed += 1
            if args.verbose:
                print(f"  PASS  {mod}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {mod}: {e}")

    # 功能测试
    from .utils import truncate, is_chinese_char, frequency_count
    assert truncate("hello world", 8) == "hello..."
    assert is_chinese_char("诗")
    assert frequency_count(["a", "b", "a"])[0] == ("a", 2)
    passed += 3

    # 数据加载测试
    from .data_loader import build_traceback_dataset
    ds = build_traceback_dataset()
    assert ds["total_poems"] > 0
    assert ds["total_images"] > 0
    passed += 2

    print(f"\n  结果: {passed}/{passed + failed} 通过")
    if failed == 0:
        print("  ALL TESTS PASSED")


# ─── 主入口 ───

def cmd_correlation(args) -> None:
    """意象关联分析"""
    from .correlation_analyzer import CorrelationAnalyzer
    analyzer = CorrelationAnalyzer()
    print_header("意象共现分析 Top20")
    pairs = analyzer.imagery_co_occurrence(min_count=3, max_pairs=20)
    for i, p in enumerate(pairs, 1):
        print(f"  {i:2d}. {p['image1']:15s} + {p['image2']:15s}  共现:{p['count']:3d}  强度:{p['strength']}%")
    print()

    print_header("意象聚类")
    clusters = analyzer.imagery_clusters(min_co_occurrence=3, max_clusters=10)
    for i, c in enumerate(clusters, 1):
        members = ", ".join(c["imagery"][:8])
        print(f"  聚类{i}: [{c['size']}个] {members}{'...' if c['size'] > 8 else ''}")
    print()


def cmd_poet(args) -> None:
    """诗人意象偏好分析"""
    from .correlation_analyzer import CorrelationAnalyzer
    analyzer = CorrelationAnalyzer()
    poet = args.poet if hasattr(args, 'poet') and args.poet else "李白"
    pref = analyzer.poet_imagery_preferences(poet, top_n=20)
    print_header(f"诗人意象偏好: {pref['poet']}")
    print_kv("意象条目总数", pref.get("total_items", 0))
    print_kv("去重意象数", pref.get("unique_imagery", 0))
    print(f"\n  高频意象 Top20:")
    for i, item in enumerate(pref.get("top_imagery", []), 1):
        print(f"  {i:2d}. {item['text']:15s}  {item['count']:4d}  独特度:{item['uniqueness_score']:.1f}")
    print()


def cmd_full_report(args) -> None:
    """生成全维度详细报告"""
    from .stats_engine import StatsEngine
    engine = StatsEngine(); engine.load_data()
    report = engine.full_dimension_report()
    fmt = args.format.lower() if args.format else "text"
    print_header(f"全维度统计报告 ({fmt})")

    if fmt == "json":
        import json
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif fmt == "text":
        for section, data in report.items():
            print(f"\n  [{section}]")
            if isinstance(data, dict):
                for k, v in list(data.items())[:10]:
                    print(f"    {k}: {v}")
            elif isinstance(data, list):
                for item in data[:5]:
                    print(f"    {item}")
    else:
        from .report_builder import save_report
        path = save_report(report, fmt=fmt)
        print(f"  报告已保存: {path}")
    print()


def cmd_dashboard(args) -> None:
    """输出仪表盘配置"""
    from .stats_engine import StatsEngine
    from .visualization_service import VisualizationService
    engine = StatsEngine(); engine.load_data()
    viz = VisualizationService(engine)
    config = viz.get_dashboard_config()
    fmt = args.format.lower() if args.format else "json"
    print_header("仪表盘配置")
    if fmt == "json":
        import json
        print(json.dumps(config, ensure_ascii=False, indent=2)[:5000])
    elif fmt == "html":
        html = viz.generate_html_page()
        fp = f"dashboard_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(fp, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML 仪表盘已保存: {fp}")
    else:
        print(json.dumps({k: v.get("title", k) for k, v in config["charts"].items()}, ensure_ascii=False, indent=2))


def cmd_compare(args) -> None:
    """诗人意象对比分析"""
    from .stats_engine import StatsEngine
    engine = StatsEngine(); engine.load_data()
    p1 = args.poet if hasattr(args, 'poet') and args.poet else "李白"
    p2 = args.poet2 if hasattr(args, 'poet2') and args.poet2 else "杜甫"
    result = engine.compare_poets(p1, p2)
    print_header(f"诗人意象对比: {p1} vs {p2}")
    print_kv("相似度", f"{result['similarity_pct']}%")
    print_kv("共有意象数", result['shared_imagery'])
    print(f"\n  共有高频意象:")
    for img, cnt in result.get("top_shared", [])[:10]:
        print(f"    {img:15s}  {cnt}")
    print(f"\n  {p1} 独有意象 Top10:")
    for img in result.get("unique_to_poet1", [])[:10]:
        print(f"    {img}")
    print(f"\n  {p2} 独有意象 Top10:")
    for img in result.get("unique_to_poet2", [])[:10]:
        print(f"    {img}")
    print()


def cmd_network(args) -> None:
    """意象网络分析"""
    from .correlation_analyzer import CorrelationAnalyzer
    analyzer = CorrelationAnalyzer()
    metrics = analyzer.imagery_network_metrics()
    print_header("意象网络度量")
    print_kv("总节点数", metrics["total_nodes"])
    print_kv("总边数", metrics["total_edges"])
    print_kv("平均度", metrics["avg_degree"])
    print(f"\n  中心节点 Top15:")
    for item in metrics.get("top_central_nodes", [])[:15]:
        print(f"    {item['node']:15s}  度={item['degree']:4d}")
    print()


COMMANDS = {
    "stats": (cmd_stats, "全维度统计摘要"),
    "top50": (cmd_top50, "Top50 高频意象"),
    "category": (cmd_category, "分类域分布"),
    "emotion": (cmd_emotion, "情感分布与交叉分析"),
    "authors": (cmd_authors, "诗人统计"),
    "correlation": (cmd_correlation, "意象关联分析"),
    "poet": (cmd_poet, "诗人意象偏好分析"),
    "compare": (cmd_compare, "诗人意象对比分析"),
    "network": (cmd_network, "意象网络分析"),
    "dashboard": (cmd_dashboard, "输出仪表盘配置"),
    "export": (cmd_export, "导出统计结果 (csv/json/html)"),
    "report": (cmd_report, "生成统计报告 (text/json/html)"),
    "full-report": (cmd_full_report, "全维度详细报告"),
    "test": (cmd_test, "运行系统自检"),
}


def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tang-stats-viz",
        description="诗歌意象多维统计与可视化系统",
    )
    parser.add_argument("command", nargs="?", default="stats",
                        choices=list(COMMANDS.keys()), help="子命令")
    parser.add_argument("--format", "-f", default="csv", help="导出/报告格式")
    parser.add_argument("--poet", "-p", default="李白", help="诗人名称（诗人分析命令）")
    parser.add_argument("--poet2", default="杜甫", help="第二个诗人（对比分析）")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        cmd_stats(None)
        return 0

    args = parser.parse_args(argv)
    cmd = args.command

    if cmd not in COMMANDS:
        print(f"未知命令: {cmd}")
        print(f"可用: {', '.join(COMMANDS.keys())}")
        return 1

    func, _ = COMMANDS[cmd]
    logger.info(f"执行: {cmd}")
    try:
        func(args)
        return 0
    except KeyboardInterrupt:
        print("\n已中断")
        return 130
    except Exception as e:
        logger.exception(f"命令异常 [{cmd}]")
        print(f"错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
