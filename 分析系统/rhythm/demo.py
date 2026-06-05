# -*- coding: utf-8 -*-
"""
古典诗词音韵格律自动分析引擎 — 演示入口
========================================
极简命令行演示，支持3个命令：
  scan   全维度扫描一首诗
  db     显示平水韵数据库统计
  compare 比较两首诗的相似度
"""
import sys


def cmd_scan(args):
    from .scansion_engine import ScansionEngine
    from .report_generator import ReportGenerator

    text = " ".join(args) if args else "白日依山尽黄河入海流欲穷千里目更上一层楼"

    engine = ScansionEngine()
    result = engine.scan(text)

    gen = ReportGenerator()
    print(gen.generate_text_report(result))


def cmd_db(args):
    from .pingshui_db import PingShuiYunDB

    db = PingShuiYunDB()
    stats = db.get_statistics()
    print(f"平水韵数据库统计")
    print(f"  总字数: {stats['total_chars']}")
    print(f"  韵部数: {stats['total_yunbu']}")
    print(f"  平声字: {stats['pingsheng']}")
    print(f"  上声字: {stats['shangsheng']}")
    print(f"  去声字: {stats['qusheng']}")
    print(f"  入声字: {stats['rusheng']}")
    print(f"  邻韵对: {stats['neighboring_pairs']}")
    print()
    print("多音字示例:")
    for ch, ybs in db.find_duoyin_chars()[:10]:
        print(f"  {ch}: {', '.join(ybs)}")


def cmd_compare(args):
    from .rhyme_similarity import RhymeComparator
    from .scansion_engine import ScansionEngine

    if len(args) < 2:
        print("用法: demo.py compare <诗1文本> <诗2文本>")
        return

    engine = ScansionEngine()
    r1 = engine.scan(args[0])
    r2 = engine.scan(args[1])

    cmp = RhymeComparator()
    result = cmp.compare(r1, r2)
    print(f"音韵相似度对比")
    print(f"  综合分:     {result.overall_score}/100")
    print(f"  韵部重叠:   {result.yunbu_overlap}/100")
    print(f"  声调相似:   {result.tone_similarity}/100")
    print(f"  密度相似:   {result.density_similarity}/100")
    print(f"  位置相似:   {result.position_similarity}/100")
    print(f"  格律相似:   {result.meter_similarity}/100")


def main():
    if len(sys.argv) < 2:
        print("用法: python -m rhythm.demo <命令> [参数]")
        print()
        print("命令:")
        print("  scan [诗歌文本]   全维度扫描")
        print("  db                平水韵统计")
        print("  compare <诗1> <诗2>  音韵相似度")
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "scan":
        cmd_scan(args)
    elif cmd == "db":
        cmd_db(args)
    elif cmd == "compare":
        cmd_compare(args)
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
