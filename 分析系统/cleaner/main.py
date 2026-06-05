# -*- coding: utf-8 -*-
"""
古典文学数据预处理与清洗系统 — 主入口
======================================
Usage:
    python -m tang_cleaner.main clean     # 批量清洗
    python -m tang_cleaner.main validate  # 结构校验
    python -m tang_cleaner.main dedup     # 去重检测
    python -m tang_cleaner.main profile   # 质量评估
    python -m tang_cleaner.main convert   # 格式转换
    python -m tang_cleaner.main encoding  # 编码检测
    python -m tang_cleaner.main backup    # 数据备份
    python -m tang_cleaner.main test      # 运行自检
"""

import os, sys, json, argparse
from datetime import datetime
from typing import Any, Dict, List


def print_header(title: str, width: int = 60) -> None:
    print(f"\n{'=' * width}\n  {title}\n{'=' * width}")


def print_kv(key: str, value: Any, indent: int = 2) -> None:
    print(f"{' ' * indent}{key:22s}: {value}")


# ─── 命令实现 ───

def cmd_clean(args) -> None:
    """批量清洗数据目录"""
    print_header("批量数据清洗")
    from .batch_cleaner import BatchCleaner
    from .config import DATA_DIR
    directory = args.dir or DATA_DIR
    print(f"  目标目录: {directory}")
    print(f"  执行阶段: clean, parse, validate")

    cleaner = BatchCleaner(max_workers=args.workers or 4)
    report = cleaner.run_pipeline(directory)

    print(f"\n  处理结果:")
    print_kv("总文件数", report.total_files)
    print_kv("处理数", report.processed)
    print_kv("成功", report.succeeded)
    print_kv("失败", report.failed)
    print_kv("成功率", f"{report.success_rate}%")
    print_kv("总修复数", report.total_fixes)
    print_kv("总错误数", report.total_errors)
    print_kv("耗时", f"{report.duration_seconds}s")

    if report.failed > 0 and not args.quiet:
        print("\n  失败文件详情:")
        for r in report.results:
            if not r.success and r.errors:
                print(f"    {r.file_name}: {r.errors[0][:100]}")
    print()


def cmd_validate(args) -> None:
    """结构校验"""
    print_header("数据结构校验")
    from .schema_validator import SchemaValidator
    from .config import DATA_DIR
    directory = args.dir or DATA_DIR
    validator = SchemaValidator(strict=args.strict or False)
    print(f"  目标目录: {directory}")
    print(f"  严格模式: {'是' if validator._strict else '否'}")

    result = validator.validate_directory(directory)

    print(f"\n  校验结果:")
    print_kv("总文件数", result["total_files"])
    print_kv("有效文件", result["valid_files"])
    print_kv("无效文件", result["invalid_files"])
    print_kv("总诗歌数", result["total_poems"])
    print_kv("总意象数", result["total_imagery"])
    print_kv("总问题数", result["total_issues"])

    if result["top_issues"]:
        print("\n  常见问题:")
        for field, cnt in result["top_issues"][:5]:
            print(f"    缺少字段'{field}': {cnt}次")

    if result["sample_issues"] and not args.quiet:
        print("\n  示例问题:")
        for issue in result["sample_issues"][:10]:
            print(f"    - {issue}")
    print()


def cmd_dedup(args) -> None:
    """去重检测"""
    print_header("重复数据检测")
    from .dedup_engine import DedupEngine
    from .preprocessor import safe_parse_json, extract_poems
    from .config import DATA_DIR
    directory = args.dir or DATA_DIR
    from .utils import list_files

    files = list_files(directory, extensions=[".json"], recursive=True)
    all_poems = []
    for fp in files:
        data, _ = safe_parse_json(fp)
        if data:
            poems = extract_poems(data)
            all_poems.extend(poems)

    print(f"  总诗歌数: {len(all_poems)}")

    engine = DedupEngine()
    mode = args.mode or "both"
    if mode == "exact" or mode == "both":
        result = engine.exact_dedup(all_poems)
        print(f"\n  精确去重:")
        print_kv("去重后", result.unique_items)
        print_kv("删除", result.duplicates_removed)
        print_kv("重复组", result.duplicate_groups)
        for s in result.sample_duplicates[:5]:
            print(f"    - {s.get('sample_title', '')}: {s['count']}次")
    if mode == "fuzzy" or mode == "both":
        result2 = engine.fuzzy_dedup(all_poems)
        print(f"\n  模糊去重 (阈值={args.threshold or 0.85}):")
        print_kv("去重后", result2.unique_items)
        print_kv("模糊重复", result2.fuzzy_duplicates)
    print()


def cmd_profile(args) -> None:
    """数据质量评估"""
    print_header("数据质量评估报告")
    from .data_profiler import DataProfiler
    from .config import DATA_DIR
    directory = args.dir or DATA_DIR
    profiler = DataProfiler()
    report = profiler.generate_quality_report(directory)

    print(f"  数据目录: {report.data_directory}")
    print_kv("总文件数", report.total_files)
    from .utils import format_file_size
    print_kv("总大小", format_file_size(report.total_size_bytes))
    print_kv("有效JSON", report.valid_json_count)
    print_kv("无效JSON", report.invalid_json_count)
    print_kv("质量评分", f"{report.overall_score}/100")

    if report.encoding_stats:
        print(f"\n  编码分布:")
        for enc, cnt in sorted(report.encoding_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"    {enc:15s}: {cnt}")

    if report.field_coverage:
        print(f"\n  字段覆盖度:")
        for field, pct in sorted(report.field_coverage.items(), key=lambda x: x[1], reverse=True):
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"    {field:15s}: {bar} {pct:.1f}%")

    if report.common_issues:
        print(f"\n  发现的问题:")
        for issue in report.common_issues:
            print(f"    - {issue}")
    print()


def cmd_encoding(args) -> None:
    """编码检测与转换"""
    print_header("编码检测")
    from .encoding_detector import detect_directory_encodings
    from .config import DATA_DIR
    directory = args.dir or DATA_DIR
    result = detect_directory_encodings(directory)

    print(f"  总文件: {result['total']}")
    print(f"\n  编码分布:")
    for enc, cnt in sorted(result['stats'].items(), key=lambda x: x[1], reverse=True):
        pct = round(cnt / max(1, result['total']) * 100, 1)
        print(f"    {enc:15s}: {cnt:4d} ({pct:5.1f}%)")

    if args.convert:
        print_header("批量编码转换")
        from .encoding_detector import batch_convert_encoding
        cv_result = batch_convert_encoding(directory, args.convert)
        print(f"  转换: {cv_result['converted']}/{cv_result['total']}成功")
    print()


def cmd_convert(args) -> None:
    """格式转换"""
    print_header("格式转换")
    from .format_converter import json_file_to_csv, csv_file_to_json, json_to_text, normalize_json_format
    from .config import DATA_DIR
    from .utils import list_files
    directory = args.dir or DATA_DIR
    files = list_files(directory, extensions=[".json"], recursive=True)

    fmt = args.format or "csv"
    count = 0
    for fp in files[:args.limit or 10]:
        try:
            if fmt == "csv":
                json_file_to_csv(fp)
            elif fmt == "txt":
                json_to_text(fp)
            elif fmt == "normalize":
                normalize_json_format(fp)
            count += 1
        except Exception as e:
            print(f"  转换失败 [{os.path.basename(fp)}]: {e}")
    print(f"  完成: {count} 个文件转换成功 ({fmt}格式)")
    print()


def cmd_backup(args) -> None:
    """数据备份"""
    print_header("数据备份")
    from .preprocessor import backup_data
    from .config import DATA_DIR
    directory = args.dir or DATA_DIR
    dest = backup_data(directory, args.output)
    if os.path.exists(dest):
        file_count = len([f for f in os.listdir(dest) if os.path.isfile(os.path.join(dest, f))])
        total_size = sum(os.path.getsize(os.path.join(dest, f)) for f in os.listdir(dest) if os.path.isfile(os.path.join(dest, f)))
        from .utils import format_file_size
        print(f"  备份路径: {dest}")
        print(f"  文件数: {file_count}")
        print(f"  总大小: {format_file_size(total_size)}")
    print()


def cmd_test(args) -> None:
    """运行自检"""
    print_header("系统自检")
    modules = ["config", "errors", "logger", "utils", "validators", "models",
               "encoding_detector", "preprocessor", "format_converter",
               "schema_validator", "dedup_engine", "batch_cleaner", "data_profiler"]
    passed = 0; failed = 0
    for mod in modules:
        try:
            __import__(f"tang_cleaner.{mod}", fromlist=[mod])
            passed += 1
            if args.verbose: print(f"  PASS  {mod}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {mod}: {e}")

    # 功能测试
    from .utils import truncate, is_chinese_char, text_similarity
    assert truncate("hello world", 8) == "hello..."
    assert is_chinese_char("诗")
    assert text_similarity("abc", "abc") == 1.0
    assert text_similarity("abc", "xyz") < 0.5
    passed += 4

    # 编码检测测试
    from .encoding_detector import detect_encoding
    from .config import DATA_DIR
    if os.path.exists(DATA_DIR):
        test_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")][:1]
        for fn in test_files:
            enc, conf = detect_encoding(os.path.join(DATA_DIR, fn))
            assert enc != "unknown" or conf == 0.0
            passed += 1

    print(f"\n  结果: {passed}/{passed + failed} 通过")
    if failed == 0: print("  ALL TESTS PASSED")


# ─── 命令注册 ───

def cmd_fix(args) -> None:
    """修复常见JSON错误"""
    print_header("JSON错误修复")
    from .preprocessor import clean_json_content, fix_common_json_errors
    from .encoding_detector import detect_encoding
    from .config import DATA_DIR
    from .utils import list_files
    directory = args.dir or DATA_DIR
    files = list_files(directory, extensions=[".json", ".txt"], recursive=True)
    total_fixes = 0
    for fp in files[:args.limit or 10]:
        with open(fp, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        cleaned, count = fix_common_json_errors(content)
        if count > 0:
            with open(fp, "w", encoding="utf-8") as f: f.write(cleaned)
            print(f"  修复: {os.path.basename(fp)} ({count}处)")
            total_fixes += count
    print(f"  总计: {total_fixes}处修复\n")


def cmd_scan(args) -> None:
    """扫描数据目录并生成文件清单"""
    print_header("数据目录扫描")
    from .encoding_detector import detect_encoding, detect_bom
    from .config import DATA_DIR
    from .utils import list_files, format_file_size
    directory = args.dir or DATA_DIR
    files = list_files(directory, extensions=[".json", ".txt", ".csv"], recursive=True)
    total_size = sum(os.path.getsize(f) for f in files)
    enc_stats = {}
    for fp in files[:args.limit or 100]:
        enc, _ = detect_encoding(fp)
        enc_stats[enc] = enc_stats.get(enc, 0) + 1
    print(f"  目录: {directory}")
    print(f"  文件: {len(files)}个, 总大小: {format_file_size(total_size)}")
    print(f"  编码分布:")
    for enc, cnt in sorted(enc_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"    {enc:12s}: {cnt:4d}")
    print()


def cmd_merge(args) -> None:
    """合并多个JSON文件"""
    print_header("JSON文件合并")
    from .format_converter import merge_json_files
    from .config import DATA_DIR
    from .utils import list_files
    directory = args.dir or DATA_DIR
    files = list_files(directory, extensions=[".json"], recursive=True)
    output = os.path.join(directory, "..", "merged_output.json")
    if args.output: output = args.output
    result = merge_json_files(files[:args.limit or 20], output)
    print(f"  合并: {min(args.limit or 20, len(files))}个文件 -> {result}\n")


def cmd_normalize(args) -> None:
    """标准化JSON格式"""
    print_header("JSON格式标准化")
    from .format_converter import normalize_json_format
    from .config import DATA_DIR
    from .utils import list_files
    directory = args.dir or DATA_DIR
    files = list_files(directory, extensions=[".json"], recursive=True)
    count = 0
    for fp in files[:args.limit or 20]:
        try:
            normalize_json_format(fp)
            count += 1
            if args.verbose: print(f"  标准化: {os.path.basename(fp)}")
        except Exception as e: print(f"  失败: {os.path.basename(fp)} - {e}")
    print(f"  完成: {count}个文件\n")


def cmd_text_clean(args) -> None:
    """中文文本清洗"""
    print_header("中文文本清洗")
    from .text_cleaner import TextCleaner
    from .config import DATA_DIR
    from .utils import list_files
    directory = args.dir or DATA_DIR
    files = list_files(directory, extensions=[".txt"], recursive=True)
    cleaner = TextCleaner()
    for fp in files[:args.limit or 10]:
        result = cleaner.clean_file(fp)
        print(f"  清洗: {os.path.basename(fp)} -> {os.path.basename(result)}")
    print(f"  统计: {cleaner.get_stats()}\n")


COMMANDS = {
    "clean": (cmd_clean, "批量清洗数据目录"),
    "validate": (cmd_validate, "数据结构校验"),
    "dedup": (cmd_dedup, "重复数据检测"),
    "profile": (cmd_profile, "数据质量评估"),
    "encoding": (cmd_encoding, "编码检测与转换"),
    "convert": (cmd_convert, "格式转换 (json→csv/txt)"),
    "backup": (cmd_backup, "数据备份"),
    "scan": (cmd_scan, "扫描数据目录"),
    "fix": (cmd_fix, "修复JSON格式错误"),
    "merge": (cmd_merge, "合并JSON文件"),
    "normalize": (cmd_normalize, "标准化JSON格式"),
    "text-clean": (cmd_text_clean, "中文文本清洗"),
    "test": (cmd_test, "运行系统自检"),
}


def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(prog="tang-cleaner", description="古典文学数据预处理与清洗系统")
    parser.add_argument("command", nargs="?", default="test", choices=list(COMMANDS.keys()), help="子命令")
    parser.add_argument("--dir", "-d", help="目标目录路径")
    parser.add_argument("--format", "-f", default="csv", help="转换格式")
    parser.add_argument("--mode", "-m", help="去重模式 (exact/fuzzy/both)")
    parser.add_argument("--threshold", type=float, default=0.85, help="模糊去重相似度阈值")
    parser.add_argument("--workers", type=int, help="并发线程数")
    parser.add_argument("--limit", type=int, default=10, help="处理文件数限制")
    parser.add_argument("--output", "-o", help="输出路径")
    parser.add_argument("--strict", action="store_true", help="严格校验模式")
    parser.add_argument("--convert", help="目标编码（用于encoding命令）")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--quiet", "-q", action="store_true", help="安静模式")

    if argv is None: argv = sys.argv[1:]
    if not argv:
        cmd_test(argparse.Namespace(verbose=False))
        return 0

    args = parser.parse_args(argv)
    cmd = args.command
    if cmd not in COMMANDS:
        print(f"未知命令: {cmd}\n可用: {', '.join(COMMANDS.keys())}")
        return 1

    func, _ = COMMANDS[cmd]
    try:
        func(args); return 0
    except KeyboardInterrupt:
        print("\n已中断"); return 130
    except Exception as e:
        print(f"错误: {e}")
        import traceback; traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())


# ─── 扩展命令 ───

def cmd_batch_all(args):
    print_header("完整流水线处理")
    from .pipeline_orchestrator import create_default_pipeline
    from .config import DATA_DIR
    directory = args.dir or DATA_DIR
    pipeline = create_default_pipeline()
    pipeline._stages["encoding"].func = lambda ctx: __import__("tang_cleaner.encoding_detector", fromlist=[""]).detect_directory_encodings(directory)
    pipeline._stages["validate"].func = lambda ctx: __import__("tang_cleaner.preprocessor", fromlist=[""]).batch_validate_directory(directory)
    pipeline._stages["quality"].func = lambda ctx: __import__("tang_cleaner.data_profiler", fromlist=[""]).DataProfiler().generate_quality_report(directory).to_dict()
    result = pipeline.run({"data_dir": directory})
    print(f"  流水线: {result['pipeline']}")
    print(f"  阶段数: {result['total_stages']}")
    print(f"  完成: {result['completed']}/{result['total_stages']}")
    print(f"  成功率: {result['success_rate']}%")
    print(f"  总耗时: {result['total_duration_seconds']}s")
    for s in result["stages"]:
        status_icon = "OK" if s["status"] == "completed" else "FAIL"
        print(f"    [{status_icon}] {s['name']}: {s['description']} ({s['duration']}s)")

def cmd_diff(args):
    print_header("目录对比")
    from .data_comparator import DataComparator
    comparator = DataComparator()
    dir1 = args.dir or "."; dir2 = args.dir2 or "."
    result = comparator.compare_directories(dir1, dir2)
    print(f"  Dir1: {result['dir1']} ({result['only_in_dir2']}个独有)")
    print(f"  Dir2: {result['dir2']}")
    print(f"  仅Dir1: {len(result['only_in_dir1'])}个, 仅Dir2: {len(result['only_in_dir2'])}个")
    print(f"  共同: {result['common']}个, 已修改: {len(result['modified'])}个")
    for m in result["modified"][:10]:
        print(f"    修改: {m['file']} ({m['size_diff']:+d} bytes)")

def cmd_export_all(args):
    print_header("批量数据导出")
    from .data_exporter import batch_export
    from .data_profiler import DataProfiler
    from .config import DATA_DIR
    directory = args.dir or DATA_DIR
    profiler = DataProfiler()
    report = profiler.generate_quality_report(directory)
    data = {"quality_report": report, "stats": profiler.quick_stats(directory), "rows": []}
    results = batch_export(data, formats=["csv", "json", "html", "txt"])
    for fmt, path in results.items():
        print(f"  [{fmt.upper()}] {path}")

def cmd_summary(args):
    print_header("系统功能概览")
    print("  古典文学数据预处理与清洗系统 V1.0")
    print()
    print("  核心功能模块:")
    modules_info = [
        ("encoding_detector", "编码自动检测与转换 (UTF-8/GBK/UTF-16等)"),
        ("preprocessor", "JSON数据清洗与格式修复"),
        ("schema_validator", "数据结构完整性校验"),
        ("text_cleaner", "中文文本专项清洗与标准化"),
        ("dedup_engine", "重复数据检测 (精确+模糊)"),
        ("format_converter", "格式转换 (JSON/CSV/TXT/TSV)"),
        ("batch_cleaner", "批量清洗流水线"),
        ("data_profiler", "数据质量评估与报告"),
        ("data_exporter", "多格式数据导出 (CSV/JSON/HTML/TXT)"),
        ("data_comparator", "数据集/目录对比"),
        ("pipeline_orchestrator", "可编排处理流水线"),
    ]
    for name, desc in modules_info:
        print(f"    {name:28s} {desc}")
    print(f"13 个命令可用: {', '.join(sorted(COMMANDS.keys()))}")

COMMANDS.update({
    "batch": (cmd_batch_all, "完整流水线处理"),
    "diff": (cmd_diff, "目录对比"),
    "export-all": (cmd_export_all, "全格式批量导出"),
    "summary": (cmd_summary, "系统功能概览"),
})
