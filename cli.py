# -*- coding: utf-8 -*-
"""
CLI 命令行工具 — 系统运维与数据管理
"""
import argparse
import json
import os
import sys
import time

from config import BASE_DIR, POEM_JSON_DIR, RAG_DB_DIR, EXPORT_DIR
from logger import get_logger

logger = get_logger("cli")


def cmd_status(args):
    """显示系统状态"""
    from config import (
        EMBED_MODEL, CHAT_MODEL, FLASK_HOST, FLASK_PORT,
        CATEGORY_NAME_MAP, KNOWN_AUTHORS,
    )
    print("=" * 60)
    print("  唐诗意象智能分析系统 — 状态检查")
    print("=" * 60)
    print(f"\n  配置概览:")
    print(f"    Embedding 模型: {EMBED_MODEL}")
    print(f"    Chat 模型:      {CHAT_MODEL}")
    print(f"    服务地址:       http://{FLASK_HOST}:{FLASK_PORT}")
    print(f"    分类维度:       {len(CATEGORY_NAME_MAP)}")
    print(f"    已知诗人:       {len(KNOWN_AUTHORS)} 位")

    print(f"\n  目录状态:")
    for name, path in [("数据目录", POEM_JSON_DIR), ("向量库", RAG_DB_DIR),
                        ("导出目录", EXPORT_DIR)]:
        exists = os.path.exists(path)
        size = ""
        if exists:
            fcount = sum(1 for f in os.listdir(path)
                         if os.path.isfile(os.path.join(path, f)))
            size = f", {fcount} 个文件"
        print(f"    {name}: {'✓' if exists else '✗'}{size}")
    print()


def cmd_scan(args):
    """扫描数据目录"""
    if not os.path.exists(POEM_JSON_DIR):
        print(f"数据目录不存在: {POEM_JSON_DIR}")
        return

    files = [f for f in os.listdir(POEM_JSON_DIR)
             if f.endswith((".json", ".txt"))]
    total_poems = 0
    total_units = 0

    print(f"\n扫描数据目录: {POEM_JSON_DIR}")
    print(f"找到 {len(files)} 个数据文件\n")

    for fname in sorted(files):
        fpath = os.path.join(POEM_JSON_DIR, fname)
        size_kb = os.path.getsize(fpath) / 1024
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            poems = data.get("诗歌集", [data]) if isinstance(data, dict) else data
            pcount = len(poems)
            ucount = sum(len(p.get("分析单元", [])) for p in poems)
            total_poems += pcount
            total_units += ucount
            print(f"  {fname:40s} {size_kb:>8.1f} KB  {pcount:>3d} 首  {ucount:>4d} 单元")
        except Exception as e:
            print(f"  {fname:40s} {size_kb:>8.1f} KB  解析失败: {e}")

    print(f"\n总计: {total_poems} 首诗歌, {total_units} 个分析单元")


def cmd_export(args):
    """导出数据"""
    from app import get_data
    from export_service import ExportService

    data = get_data()
    traceback = data.get("traceback", [])
    fmt = args.format or "csv"

    if fmt == "csv":
        path = ExportService.export_traceback_to_csv(traceback)
    elif fmt == "json":
        path = ExportService.export_to_json(data)
    elif fmt == "report":
        from analytics import StatsService
        service = StatsService(traceback)
        path = ExportService.export_summary_report(service.summary_report())
    else:
        print(f"不支持格式: {fmt}")
        return

    fsize = os.path.getsize(path) / 1024
    print(f"导出成功: {path} ({fsize:.1f} KB)")


def cmd_clear_cache(args):
    """清理缓存"""
    from cache import memory_cache, file_cache
    memory_cache.clear()
    file_cache.clear()
    from app import clear_data_cache
    clear_data_cache()
    print("缓存已清理")


def cmd_list_exports(args):
    """列出导出文件"""
    from export_service import ExportService
    files = ExportService.list_exports()
    if not files:
        print("暂无导出文件")
        return
    print(f"\n导出目录: {EXPORT_DIR}")
    print(f"{'文件名':40s} {'大小':>10s}  {'修改时间'}")
    print("-" * 70)
    for f in files:
        size = f["size"] / 1024 if f["size"] > 1024 else f["size"]
        unit = "KB" if f["size"] > 1024 else "B"
        mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f["mtime"]))
        print(f"  {f['name']:38s} {size:>8.2f} {unit}  {mtime}")


def cmd_check_rag(args):
    """检查向量库状态"""
    import chromadb
    if not os.path.exists(RAG_DB_DIR):
        print("向量库不存在，请先运行 build_rag.py")
        return
    client = chromadb.PersistentClient(path=RAG_DB_DIR)
    try:
        collection = client.get_collection(name="poems")
        count = collection.count()
        print(f"\n向量库状态:")
        print(f"  路径: {RAG_DB_DIR}")
        print(f"  集合: poems")
        print(f"  向量数: {count}")
        if count > 0:
            sample = collection.peek()
            print(f"  示例文档:")
            for i, doc in enumerate(sample["documents"][:3]):
                meta = sample["metadatas"][i]
                print(f"    [{i+1}] 《{meta.get('标题','')}》{meta.get('作者','')} ({len(doc)}字)")
    except Exception as e:
        print(f"读取向量库失败: {e}")


def cmd_build_rag(args):
    """构建向量库"""
    from build_rag import main as build_main
    build_main()


def cmd_test(args):
    """运行单元测试"""
    import subprocess
    test_path = os.path.join(BASE_DIR, "tests")
    cmd = [sys.executable, "-m", "pytest", test_path, "-v"]
    if args.verbose:
        cmd.append("-v")
    print(f"运行测试: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=BASE_DIR)
    sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(
        description="唐诗意象智能分析系统 — CLI 管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python cli.py status          查看系统状态
  python cli.py scan            扫描数据目录
  python cli.py export --format csv   导出 CSV
  python cli.py test            运行单元测试
  python cli.py check-rag       检查向量库
  python cli.py build-rag       构建向量库
""",
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # status
    p = subparsers.add_parser("status", help="显示系统状态")
    p.set_defaults(func=cmd_status)

    # scan
    p = subparsers.add_parser("scan", help="扫描数据目录")
    p.set_defaults(func=cmd_scan)

    # export
    p = subparsers.add_parser("export", help="导出数据")
    p.add_argument("--format", "-f", choices=["csv", "json", "report"],
                    default="csv", help="导出格式")
    p.set_defaults(func=cmd_export)

    # clear-cache
    p = subparsers.add_parser("clear-cache", help="清理缓存")
    p.set_defaults(func=cmd_clear_cache)

    # list-exports
    p = subparsers.add_parser("list-exports", help="列出导出文件")
    p.set_defaults(func=cmd_list_exports)

    # check-rag
    p = subparsers.add_parser("check-rag", help="检查向量库状态")
    p.set_defaults(func=cmd_check_rag)

    # build-rag
    p = subparsers.add_parser("build-rag", help="构建向量库")
    p.set_defaults(func=cmd_build_rag)

    # test
    p = subparsers.add_parser("test", help="运行单元测试")
    p.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    p.set_defaults(func=cmd_test)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return

    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n操作已取消")
    except Exception as e:
        logger.exception("CLI 命令执行失败")
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
