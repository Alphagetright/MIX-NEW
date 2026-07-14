# MIX-NEW — 唐诗 AI 分析生态系统

古典诗歌文本结构化分析、LLM 标注生产、Agent 驱动数据运维——三个独立子系统 + 一个 AI 开发工作流引擎。

→ **[在线作品集](https://alphagetright.github.io/MIX-NEW/)**（GitHub Pages）

## Architecture

```
原始诗歌文本 → Pipeline 解析 → 格律校验 → 意象提取 → ChromaDB 向量嵌入 → RAG 问答 → ECharts 可视化
                                      ↑
                         Poem Lab: 三段式 Meta-Prompting 自动标注
                                      ↑
                    TangCLI: Agent Loop + Tool Registry 自然语言运维
```

## 项目概览

| 项目 | 类型 | Role | 核心技术 |
|------|------|------|----------|
| **诗歌意象分析系统** | 全栈 Web 应用 | Independent Developer — 架构设计、Pipeline 编排、全栈开发 | Flask, ChromaDB RAG, ECharts, 17-module rhythm engine |
| **Poem Lab v2** | LLM 标注引擎 | Independent Developer — 架构设计、Meta-Prompting 流程、并行调度 | 三段式 Meta-Prompting, ThreadPoolExecutor, SSE, SQLite |
| **TangCLI** | Agent CLI 工具 | Independent Developer — Agent Loop 架构、Tool Registry 实现 | Function Calling, REPL, PyInstaller, Flask |
| **AI 开发工作流引擎** | 元工具/基础设施 | Independent Developer — Hook 系统、双轨迭代模型、插件市场 | Hooks, JSONL, YAML, Skill 编排 |

## Features

### 零依赖格律引擎
`分析系统/rhythm/` — 17 个模块，纯 Python 标准库实现平水韵 106 韵部的平仄判断、押韵检测、对仗识别、文本校勘。不依赖任何 NLP 库或外部词典。

### 三段式 Meta-Prompting
Poem Lab 的核心创新——不是手写 prompt，是让 LLM 自己设计 prompt：
1. **Phase 1** — 自然语言需求解析为结构化表头
2. **Phase 2** — 自动生成专用标注提示词 + 列映射
3. **Phase 3** — 质量校验试跑，通过后才启动批量执行

### Agent Loop 架构
TangCLI 的自主决策引擎：自然语言意图 → LLM 推理 → Function Calling 工具选择 → 执行 → 结果反馈。14 个工具封装为 OpenAI function-calling schema，注册表可扩展。

### 双轨迭代工作流
AI 开发工作流引擎：PostToolUse/Stop Hooks → JSONL 事件队列 → CHANGELOG.md (what) + thoughts.md (why) → session.md 交接。9 个自定义 Skill 标准化打包为 3 个插件组。

## Results

- **1,336** 首杜甫诗 + **313** 首全唐诗结构化处理
- **12,738** 个分析单元，**4,896** 条意象标注
- **11 MB** 主数据集 + **50 MB** 逐首分析 JSON
- 格律引擎 **106** 韵部，**17** 模块，零外部依赖
- Poem Lab **55** 路由 + **12** 套标注模板 + 三维质量评分
- TangCLI **28** 模块 + **15** 子命令 + **14** 注册工具
- **3** 项软件著作权已申请
- 全链路闭环：数据清洗 → LLM 推理 → 向量检索 → 可视化交付

## 本地运行

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

## License

三个子系统均已申请软件著作权。源码开放查阅。
