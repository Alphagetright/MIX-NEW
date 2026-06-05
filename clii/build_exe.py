# -*- coding: utf-8 -*-
"""
TangCLI 便携打包脚本
====================
使用 PyInstaller 将整个项目打包为独立文件夹。
拷贝 dist/TangCLI/ 到任意 Windows 电脑即可运行。

运行方式:
    python build_exe.py

输出:
    dist/TangCLI/
    ├── TangCLI.exe          ← 双击启动
    ├── poem_json/           ← 诗歌数据
    ├── poem_lab/prompts/    ← 提示词模板
    ├── poem_lab/templates/  ← 分析模板
    ├── cli_ops/web/templates/ ← Web 模板
    └── ...                  ← Python 运行时 + 依赖
"""

import os
import sys
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))

# ── 数据目录（需要打包进 EXE 的非代码文件） ──
DATA_DIRS = [
    ("poem_json", "poem_json"),                      # 唐诗 JSON 数据
    ("dufu/poem-json", "dufu/poem-json"),             # 杜甫分类数据
    ("poem_lab/prompts", "poem_lab/prompts"),          # Meta-prompt 模板
    ("poem_lab/templates", "poem_lab/templates"),      # 分析模板
    ("cli_ops/web/templates", "cli_ops_web_templates"),  # Flask 模板
]

# 构建 add-data 参数
ADD_DATA = []
for src_rel, dst_name in DATA_DIRS:
    src = os.path.join(BASE, src_rel)
    if os.path.isdir(src):
        # Windows 分隔符
        ADD_DATA.append(f"{src};{dst_name}")
        print(f"  DATA: {src_rel} -> {dst_name}")
    else:
        print(f"  SKIP: {src_rel} (not found)")

# ── 隐藏导入（PyInstaller 可能漏掉的动态 import） ──
HIDDEN_IMPORTS = [
    "cli_ops",
    "cli_ops.cli_main",
    "cli_ops.repl",
    "cli_ops.session",
    "cli_ops.rich_ui",
    "cli_ops.tools",
    "cli_ops.agent_loop",
    "cli_ops.llm_client",
    "cli_ops.models",
    "cli_ops.config",
    "cli_ops.logger",
    "cli_ops.errors",
    "cli_ops.utils",
    "cli_ops.validators",
    "cli_ops.cache_manager",
    "cli_ops.export_engine",
    "cli_ops.data_scanner",
    "cli_ops.health_checker",
    "cli_ops.report_generator",
    "cli_ops.batch_processor",
    "cli_ops.preprocessor",
    "cli_ops.monitor",
    "cli_ops.web",
    "cli_ops.web.app",
    "poem_lab",
    "poem_lab.app",
    "poem_lab.lib",
    "poem_lab.lib.meta_prompts",
    "poem_lab.lib.schema_engine",
    "poem_lab.lib.llm_client",
    "poem_lab.lib.config_loader",
    "poem_lab.lib.persistence",
    "poem_lab.lib.quality_scorer",
    "poem_lab.lib.report_writer",
    "poem_lab.lib.annotation_tools",
    "poem_lab.lib.template_library",
    "poem_lab.lib.corpus",
    "poem_lab.lib.preprocessor",
    "flask",
    "rich",
    "chromadb",
    "requests",
    "openpyxl",
]

# ── PyInstaller 参数 ──
CMD = [
    sys.executable, "-m", "PyInstaller",
    "--name", "TangCLI",
    "--onefile",
    "--console",
    "--clean",
    "--noconfirm",
    f"--add-data", ";".join(ADD_DATA) if len(ADD_DATA) > 1 else ADD_DATA[0] if ADD_DATA else "",
]

# 由于 --add-data 需要多个，分开追加
args = [
    sys.executable, "-m", "PyInstaller",
    "--name", "TangCLI",
    "--onedir",              # 用 onedir 而不是 onefile，因为数据文件多
    "--console",
    "--clean",
    "--noconfirm",
    "--distpath", os.path.join(BASE, "dist"),
    "--workpath", os.path.join(BASE, "build_temp"),
    "--specpath", BASE,
]

for src_rel, dst_name in DATA_DIRS:
    src = os.path.join(BASE, src_rel)
    if os.path.isdir(src):
        args.append("--add-data")
        args.append(f"{src}{os.pathsep}{dst_name}")

for imp in HIDDEN_IMPORTS:
    args.append("--hidden-import")
    args.append(imp)

# 入口文件
args.append(os.path.join(BASE, "cli_ops", "launcher.py"))


def build():
    print("=" * 60)
    print("  TangCLI 便携打包")
    print("=" * 60)

    print(f"\n数据目录:")
    for src_rel, dst in DATA_DIRS:
        src = os.path.join(BASE, src_rel)
        status = "OK" if os.path.isdir(src) else "MISSING"
        print(f"  [{status}] {src_rel}")

    print(f"\n隐藏导入: {len(HIDDEN_IMPORTS)} 个模块")
    print(f"\n开始打包...\n")

    import subprocess
    result = subprocess.run(args, cwd=BASE)

    if result.returncode != 0:
        print(f"\n打包失败 (exit code {result.returncode})")
        sys.exit(1)

    # 打包后复制 poem_lab 的 prompts 和 templates 到 dist
    dist_dir = os.path.join(BASE, "dist", "TangCLI")
    for src_rel, dst_name in DATA_DIRS:
        src = os.path.join(BASE, src_rel)
        dst = os.path.join(dist_dir, dst_name)
        if os.path.isdir(src) and not os.path.exists(dst):
            shutil.copytree(src, dst)
            print(f"  复制数据: {dst_name}")

    print(f"\n{'='*60}")
    print(f"  打包完成!")
    print(f"  输出: {dist_dir}")
    print(f"  启动: {os.path.join(dist_dir, 'TangCLI.exe')}")
    print(f"{'='*60}")
    print(f"\n  将 dist/TangCLI/ 文件夹拷贝到任意电脑即可使用。")
    print(f"  前提: 目标电脑需配置 LLM（本地 LM Studio 或 DeepSeek API）")
    print()


if __name__ == "__main__":
    build()
