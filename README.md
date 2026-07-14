# MIX-NEW — 唐诗 AI 分析生态系统

古典诗歌文本结构化分析、LLM 标注生产、Agent 驱动数据运维——三个独立子系统共享统一诗歌语料库。

## 作品集

→ **[在线作品集](https://alphagetright.github.io/MIX-NEW/)**（GitHub Pages）

## 系统概览

```
MIX-NEW/
├── 分析系统/              — 诗歌意象分析系统（Flask + RAG + 格律引擎）
├── 古典诗歌.../poem_lab/  — Poem Lab v2：LLM 标注引擎（Meta-Prompting）
├── clii/cli_ops/          — TangCLI：Agent 驱动运维工具（28 模块）
└── poem_json/             — 共享诗歌语料库
```

| 系统 | 定位 | 技术要点 |
|------|------|----------|
| **诗歌意象分析系统** | 全栈 Web 应用，意象分析 + 可视化 | Flask、ChromaDB RAG、ECharts、17 模块格律引擎（纯标准库，覆盖平水韵 106 韵部） |
| **Poem Lab v2** | LLM 标注生产流水线 | 三段式 meta-prompting、ThreadPoolExecutor 并行、checkpoint 断点续传、SSE 流式推送、SQLite |
| **TangCLI** | 自然语言驱动 CLI 运维工具 | Agent Loop + Tool Registry、15 子命令、REPL 交互模式、PyInstaller 打包 |

## 数据规模

- **1,336** 首杜甫诗逐一分析（50 MB 结构化 JSON）
- **313** 首唐诗，**12,738** 个分析单元，**4,896** 条意象标注
- **11 MB** 主标注数据集，每条含 15+ 维度标签
- ChromaDB 向量库支撑 RAG 问答

## 核心技术决策

### 零依赖格律引擎
`分析系统/rhythm/` 目录下 17 个模块，纯 Python 标准库实现平水韵 106 韵部的平仄判断、押韵检测、对仗识别、文本校勘。不依赖任何 NLP 库、外部词典——完全是算法层面的实现。

### 三段式 Meta-Prompting（Poem Lab）
不是手写 prompt，是让 LLM 自己设计 prompt：
1. **阶段一** — 自然语言需求解析为结构化表头
2. **阶段二** — 自动生成专用标注提示词 + 列映射
3. **阶段三** — 质量校验试跑，通过后才启动批量执行

### Agent Loop 架构（TangCLI）
Tool Registry（14 个工具封装为 OpenAI function-calling schema）+ Agent Loop（自然语言意图 → LLM 推理 → 工具选择 → 执行 → 结果反馈）。模式可复用——注册表接受任何带 schema 的 callable。

## 本地运行

各子系统独立启动：

```bash
# 诗歌分析系统（端口 5000）
cd 分析系统 && python app.py

# Poem Lab（端口 5000）
cd 古典诗歌文本结构化标注生产系统3/poem_lab && python app.py

# TangCLI Web 控制台（端口 5001）
cd clii/cli_ops/web && python app.py

# TangCLI REPL 模式
python clii/cli_ops/cli_main.py
```

**环境要求：** Python 3.10+，LM Studio（LLM 功能可选），`pip install flask chromadb`

## 著作权

三个子系统均已申请软件著作权。源码开放查阅。
