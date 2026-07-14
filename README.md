# MIX-NEW — Tang Poetry AI Analysis Ecosystem

A multi-system workspace for classical Chinese poetry analysis, structured annotation, and LLM-driven data operations. Three independent subsystems sharing a unified poetry corpus.

## Portfolio

→ **[View Portfolio Page](https://alphagetright.github.io/MIX-NEW/)** (GitHub Pages)

## System Overview

```
MIX-NEW/
├── 分析系统/              — Poetry Imagery Analysis System (Flask + RAG + Prosody)
├── 古典诗歌.../poem_lab/  — Poem Lab v2: LLM Annotation Engine (Meta-Prompting)
├── clii/cli_ops/          — TangCLI: Agent-Driven Operations Toolkit (28 modules)
└── poem_json/             — Shared poetry corpus (DBpia JSON preprocessed)
```

| System | Role | Tech Highlights |
|--------|------|-----------------|
| **Poetry Analysis System** | Full-stack web app for imagery analysis + visualization | Flask, ChromaDB RAG, ECharts, 17-module prosody engine (stdlib only, 106 rhyme categories) |
| **Poem Lab v2** | Production LLM annotation pipeline | 3-phase meta-prompting, ThreadPoolExecutor, checkpoint/resume, SSE streaming, SQLite |
| **TangCLI** | Natural-language-driven CLI ops toolkit | Agent Loop + Tool Registry, 15 subcommands, REPL mode, PyInstaller packaging |

## Scale

- **1,336** Du Fu poems analyzed individually (50 MB structured JSON)
- **313** Tang poems with **12,738** analysis units and **4,896** imagery items
- **11 MB** main annotation dataset with 15+ dimension tags per item
- **RAG** vector store (ChromaDB) powering LLM Q&A

## Key Technical Decisions

### Zero-Dependency Prosody Engine
The rhythm analysis engine (`分析系统/rhythm/`) implements Pingshui rhyme system (平水韵, 106 categories) entirely in Python stdlib — no NLP libraries, no external dictionaries. Pure algorithmic approach to tone pattern matching, rhyme detection, antithesis identification, and textual collation.

### Three-Phase Meta-Prompting (Poem Lab)
Instead of hand-crafting prompts for each annotation task, the system uses an LLM to design the prompt:
1. **Phase 1** — Parse natural language requirements into structured headers
2. **Phase 2** — Auto-generate task-specific prompts + column mapping
3. **Phase 3** — Quality validation trial run before batch execution

### Agent Loop Architecture (TangCLI)
Tool Registry (14 tools as OpenAI function-calling schemas) + Agent Loop (NL intent → LLM reasoning → tool selection → execution → result feedback). The pattern is reusable beyond poetry — the registry accepts any callable with a schema.

## Running Locally

Each subsystem starts independently:

```bash
# Poetry Analysis System (port 5000)
cd 分析系统 && python app.py

# Poem Lab (port 5000)
cd 古典诗歌文本结构化标注生产系统3/poem_lab && python app.py

# TangCLI Web Dashboard (port 5001)
cd clii/cli_ops/web && python app.py

# TangCLI REPL
python clii/cli_ops/cli_main.py
```

**Requirements:** Python 3.10+, LM Studio (optional, for LLM features), `pip install flask chromadb` (see individual subsystem configs).

## License

Software copyrights filed for all three subsystems. Source code available for review.
