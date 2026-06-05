# -*- coding: utf-8 -*-
"""
软著申请材料生成工具
—— 将项目所有源代码汇总到单一文件，附带功能描述与开发目的说明
"""
import os
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "软著_源代码汇总.txt")

# 需要排除的目录和文件
EXCLUDE_DIRS = {"__pycache__", "rag_db", "logs", "cache", "exports", ".pytest_cache", "__MACOSX"}
EXCLUDE_FILES = {
    "source.txt", "requirements.txt",
    "generate_soft_copyright.py",  # 本脚本自身
    "软著_源代码汇总.txt",         # 已生成的输出
}
BINARY_EXTS = {".bin", ".sqlite3", ".db"}

# 按模块分组（软著注重架构层次）
MODULE_GROUPS = [
    ("一、系统配置模块", ["config.py"]),
    ("二、日志系统", ["logger.py"]),
    ("三、异常处理与数据校验", ["errors.py", "validators.py"]),
    ("四、通用工具函数", ["utils.py"]),
    ("五、中间件与请求追踪", ["middleware.py"]),
    ("六、缓存服务", ["cache.py"]),
    ("七、数据模型层", ["models.py"]),
    ("八、数据统计分析服务", ["analytics.py"]),
    ("九、数据导出服务", ["export_service.py"]),
    ("十、数据预处理", ["preprocessor.py"]),
    ("十一、系统监控", ["monitor.py"]),
    ("十二、RAG 构建脚本", ["build_rag.py"]),
    ("十三、RAG 检索与问答引擎", ["query_rag.py"]),
    ("十四、CLI 命令行工具", ["cli.py"]),
    ("十五、Flask Web 主程序", ["app.py", "admin.py"]),
    ("十六、前端界面", ["templates/index.html", "templates/admin.html"]),
    ("十七、数据转换工具", ["json_to_3csv.py"]),
    ("十八、文件切分工具", ["split_1kb.py"]),
    ("十九、单元测试", [
        "tests/test_config.py", "tests/test_validators.py",
        "tests/test_analytics.py", "tests/test_cache.py",
        "tests/test_export.py", "tests/test_models.py",
        "tests/test_preprocessor.py", "tests/test_middleware.py",
        "tests/test_cli.py", "tests/test_utils.py",
    ]),
]

SOFTWARE_NAME = "唐诗意象智能分析系统"
VERSION = "V1.0"


def get_file_info(filepath):
    """获取文件信息：行数、大小"""
    if not os.path.exists(filepath):
        return None, None
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    lines = content.count("\n") + 1 if content else 0
    size_kb = os.path.getsize(filepath) / 1024
    return content, lines, size_kb


def collect_orphan_files():
    """收集未被分组的 Python 文件"""
    grouped = set()
    for _, files in MODULE_GROUPS:
        for f in files:
            grouped.add(os.path.normpath(f))
    orphans = []
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if f.endswith(".py") and not f.startswith("_"):
                fpath = os.path.normpath(os.path.join(root, f))
                rel = os.path.relpath(fpath, BASE_DIR)
                if rel not in grouped and rel not in EXCLUDE_FILES:
                    orphans.append(rel)
    return orphans


def main():
    print("=" * 60)
    print(f"  {SOFTWARE_NAME} — 软著申请材料生成")
    print(f"  版本: {VERSION}")
    print(f"  生成日期: {datetime.date.today()}")
    print("=" * 60)

    output_lines = []
    total_lines = 0
    file_count = 0

    # ── 文件头 ──
    output_lines.append("=" * 80)
    output_lines.append(f"  软件名称：{SOFTWARE_NAME}")
    output_lines.append(f"  版本号：{VERSION}")
    output_lines.append(f"  开发完成日期：{datetime.date.today()}")
    output_lines.append(f"  生成日期：{datetime.date.today()}")
    output_lines.append("=" * 80)
    output_lines.append("")

    # ── 一、功能描述与开发目的 ──
    output_lines.append("=" * 80)
    output_lines.append("一、软件功能描述与开发目的")
    output_lines.append("=" * 80)
    output_lines.append("")

    output_lines.append("【开发目的】")
    output_lines.append("")
    output_lines.append(
        "唐诗意象智能分析系统是一款面向中国古典诗歌研究的计算机辅助分析平台。"
        "该系统以认知诗学理论为指导，综合运用自然语言处理、向量检索（RAG）"
        "和大语言模型技术，实现对唐诗意象的系统化提取、分类标注、情感分析和"
        "多维度统计。"
    )
    output_lines.append("")
    output_lines.append(
        "系统旨在解决传统文学研究中意象标注工作量大、主观性强、难以跨文本"
        "比较的问题，为古典文学研究者、教育工作者和诗歌爱好者提供一个集数据"
        "管理、智能检索、认知分析和可视化展示于一体的研究工具。"
    )
    output_lines.append("")

    output_lines.append("【主要功能】")
    output_lines.append("")
    output_lines.append("1. 意象数据管理与溯源")
    output_lines.append("   - 从 JSON/TXT 文件中批量加载诗歌意象标注数据")
    output_lines.append("   - 自动去重、分类映射、多维度字段展示")
    output_lines.append("   - 支持意象文本搜索、分类域筛选、情感倾向筛选")
    output_lines.append("   - 分页浏览与删除/恢复（回收站机制）")
    output_lines.append("")

    output_lines.append("2. 数据可视化分析")
    output_lines.append("   - 核心意象 Top50 频次柱状图（ECharts）")
    output_lines.append("   - 意象分类域分布图")
    output_lines.append("   - 图表点击联动筛选")
    output_lines.append("   - 全屏查看与自适应布局")
    output_lines.append("")

    output_lines.append("3. RAG 智能问答")
    output_lines.append("   - 基于向量检索（ChromaDB + Embedding API）的语义检索")
    output_lines.append("   - 支持按诗人过滤检索")
    output_lines.append("   - 流式 SSE 输出，多轮对话追问")
    output_lines.append("   - 检索结果实时展示与全文展开")
    output_lines.append("")

    output_lines.append("4. 认知诗学意象解析")
    output_lines.append("   - 基于大语言模型的单意象深度解析")
    output_lines.append("   - 感知层、文化层、情感层、结构层、跨诗比较五维分析")
    output_lines.append("   - 侧边抽屉式交互，支持多轮追问")
    output_lines.append("   - 解析结果缓存，避免重复请求")
    output_lines.append("")

    output_lines.append("5. 多维度统计分析")
    output_lines.append("   - 意象频次统计与排序")
    output_lines.append("   - 分类域分布（大类/子类二级统计，含百分比）")
    output_lines.append("   - 诗人维度统计（意象数、诗作数、Top5 高频意象）")
    output_lines.append("   - 情感类别与情感极性分布")
    output_lines.append("   - 感知通道分布统计")
    output_lines.append("   - 情感×分类域交叉分析")
    output_lines.append("")

    output_lines.append("6. 数据导出与备份")
    output_lines.append("   - CSV 格式溯源数据导出（utf-8-sig 编码，兼容 Excel）")
    output_lines.append("   - JSON 格式完整数据导出")
    output_lines.append("   - 统计分析报告导出")
    output_lines.append("   - 导出文件管理与批量清理")
    output_lines.append("")

    output_lines.append("7. 系统管理与运维")
    output_lines.append("   - 系统状态面板（诗歌数、意象数、缓存状态、数据库状态）")
    output_lines.append("   - 数据缓存手动刷新与清理")
    output_lines.append("   - 集中化配置管理")
    output_lines.append("   - 分级日志系统（控制台 + 文件滚动）")
    output_lines.append("   - 统一异常处理与请求校验")
    output_lines.append("   - 请求中间件（请求标识、计时、CORS）")
    output_lines.append("   - CLI 命令行管理工具")
    output_lines.append("   - 系统资源监控（磁盘、内存、CPU）")
    output_lines.append("")

    output_lines.append("8. 数据预处理与校验")
    output_lines.append("   - JSON 格式清洗（去除 Markdown 包裹、修正尾逗号）")
    output_lines.append("   - 批量数据校验与结构验证")
    output_lines.append("   - 自动备份机制")
    output_lines.append("   - 数据模型层（Poem、AnalysisUnit 等数据类）")
    output_lines.append("")

    output_lines.append("【技术架构】")
    output_lines.append("")
    output_lines.append("  - 后端框架：Flask (Python 3.13)")
    output_lines.append("  - 前端框架：原生 HTML/CSS/JavaScript + ECharts")
    output_lines.append("  - 向量数据库：ChromaDB (余弦相似度)")
    output_lines.append("  - 大模型接口：本地 LLM API (兼容 OpenAI 格式)")
    output_lines.append("  - 通信协议：SSE (Server-Sent Events) 流式输出")
    output_lines.append("  - 数据格式：JSON / CSV")
    output_lines.append("  - 缓存策略：内存缓存 + 文件缓存（TTL 支持）")
    output_lines.append("")

    # ── 代码行数统计 ──
    output_lines.append("=" * 80)
    output_lines.append("二、源代码文件清单与行数统计")
    output_lines.append("=" * 80)
    output_lines.append("")

    file_stats = []

    for group_name, group_files in MODULE_GROUPS:
        output_lines.append(f"\n{group_name}")
        output_lines.append("-" * 60)
        for relpath in group_files:
            abspath = os.path.join(BASE_DIR, relpath)
            content, lines, size_kb = get_file_info(abspath)
            if content is None:
                output_lines.append(f"  [文件未找到] {relpath}")
                continue
            file_stats.append((relpath, lines, size_kb))
            output_lines.append(f"  {relpath}  ({lines} 行, {size_kb:.1f} KB)")
        output_lines.append("")

    # 孤儿文件
    orphans = collect_orphan_files()
    if orphans:
        output_lines.append("\n其他文件：")
        output_lines.append("-" * 60)
        for relpath in orphans:
            abspath = os.path.join(BASE_DIR, relpath)
            content, lines, size_kb = get_file_info(abspath)
            if content is None:
                continue
            file_stats.append((relpath, lines, size_kb))
            output_lines.append(f"  {relpath}  ({lines} 行, {size_kb:.1f} KB)")
        output_lines.append("")

    total_code_lines = sum(s[1] for s in file_stats)
    total_files = len(file_stats)
    output_lines.append(f"\n总计：{total_files} 个文件，{total_code_lines} 行代码\n")

    # ── 三、源代码正文 ──
    output_lines.append("=" * 80)
    output_lines.append("三、源代码正文")
    output_lines.append("=" * 80)
    output_lines.append("")
    output_lines.append(f"（共计 {total_files} 个源文件，{total_code_lines} 行）")
    output_lines.append("")

    for group_name, group_files in MODULE_GROUPS:
        for relpath in group_files:
            abspath = os.path.join(BASE_DIR, relpath)
            content, lines, size_kb = get_file_info(abspath)
            if content is None:
                continue

            output_lines.append("")
            output_lines.append("=" * 80)
            output_lines.append(f"  文件：{relpath}  ({lines} 行, {size_kb:.1f} KB)")
            output_lines.append("=" * 80)
            output_lines.append("")

            # 写文件内容，跳过空行（软著提交只需有效代码行）
            line_num = 0
            for line in content.split("\n"):
                line = line.rstrip()
                if not line:
                    continue
                line_num += 1
                output_lines.append(f"{line_num:>5}  {line}")

            output_lines.append("")
            output_lines.append(f"-- 文件结束：{relpath} --")
            output_lines.append("")

    # 写入输出文件
    full_text = "\n".join(output_lines)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"\n=== 生成完毕！===")
    print(f"   输出文件：{OUTPUT_FILE}")
    print(f"   总文件数：{total_files}")
    print(f"   总行数：{total_code_lines}")
    print(f"   总大小：{os.path.getsize(OUTPUT_FILE) / 1024:.1f} KB")
    print(f"\n提示：此文件可直接用于软著申请材料中的源代码部分。")
    print(f"   根据需要截取前 30 页和后 30 页提交即可。")


if __name__ == "__main__":
    main()
