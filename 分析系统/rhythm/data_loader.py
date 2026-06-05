# -*- coding: utf-8 -*-
"""
古典诗词音韵格律分析引擎 — 诗歌数据加载与适配
============================================
支持多种数据源格式（JSON、TXT、CSV）的诗歌数据加载，
自动提取标题、作者、正文并适配为统一格式。
"""
import csv
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from .errors import PoemDataError, safe_call
from .logger import get_logger
from .models import PoemMetadata

logger = get_logger("data_loader")


def extract_chinese_lines(text: str) -> List[str]:
    """从文本中提取中文诗句（按标点符号分割）"""
    # 按中文标点分割：句号、问号、感叹号、分号
    segments = re.split(r"[。？！；\n\r]+", text)
    lines = [s.strip() for s in segments if s.strip()]
    # 过滤掉非中文内容（保留至少2个汉字的行）
    chinese_lines = []
    for line in lines:
        chinese_chars = "".join(c for c in line if "一" <= c <= "鿿")
        if len(chinese_chars) >= 3:  # 至少3个汉字
            chinese_lines.append(chinese_chars)

    # 如果按标点分割不足2句，按字数分割（无标点文本）
    if len(chinese_lines) < 2:
        flat = "".join(chinese_lines) if chinese_lines else "".join(
            c for c in text if "一" <= c <= "鿿"
        )
        if len(flat) >= 10:
            maybe_len = _guess_line_length(flat)
            if maybe_len > 0:
                chinese_lines = _split_by_length(flat, maybe_len)

    return chinese_lines


def normalize_line(line: str) -> str:
    """标准化单句：去空格、去标点、保留汉字"""
    return "".join(c for c in line.strip() if "一" <= c <= "鿿" or c == "，")


# ─── JSON加载策略 ───


def _detect_json_poem_structure(item: dict) -> Optional[Dict[str, Any]]:
    """智能检测JSON中诗歌的结构"""
    result = {}
    # 尝试常见字段名
    title_keys = ["标题", "title", "题目", "诗题", "诗名", "name"]
    author_keys = ["作者", "author", "诗人", "poet"]
    text_keys = ["原文", "text", "content", "内容", "正文", "原诗", "poem"]
    lines_keys = ["诗句", "lines", "paragraphs", "paragraph"]

    title = None
    for k in title_keys:
        if k in item and item[k]:
            title = str(item[k]).strip()
            break
    if not title:
        title = "无题"

    author = None
    for k in author_keys:
        if k in item and item[k]:
            author = str(item[k]).strip()
            break
    if not author:
        author = "佚名"

    # 如果有诗句列表，优先使用
    text = None
    for k in lines_keys:
        if k in item and item[k]:
            if isinstance(item[k], list):
                text = "".join(str(s) for s in item[k])
            elif isinstance(item[k], str):
                text = item[k]
            break

    if not text:
        for k in text_keys:
            if k in item and item[k]:
                text = str(item[k])
                break

    line_count = None
    if "句数" in item:
        try:
            line_count = int(item["句数"])
        except (ValueError, TypeError):
            pass
    if line_count is None and "line_count" in item:
        try:
            line_count = int(item["line_count"])
        except (ValueError, TypeError):
            pass

    if not text:
        return None

    return {
        "title": title,
        "author": author,
        "text": text,
        "line_count": line_count,
    }


# ─── 主加载函数 ───


def load_poem_from_json(file_path: str) -> List[PoemMetadata]:
    """从JSON文件中加载诗歌

    支持格式：
    - 列表 [poem, poem, ...]
    - 字典 { "key": [poem, poem, ...] }
    - 单个诗歌对象 { "标题": ..., "作者": ..., "原文": ... }
    """
    if not os.path.exists(file_path):
        raise PoemDataError(f"文件不存在: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    items = _normalize_json_input(raw)
    poems = []

    for item in items:
        try:
            parsed = _detect_json_poem_structure(item)
            if parsed is None:
                continue

            text = parsed["text"]
            lines = extract_chinese_lines(text)

            # 如果无法从正文分割出多句，尝试按固定字数分割
            if len(lines) < 2 and len(text) > 10:
                maybe_len = _guess_line_length(text)
                if maybe_len > 0:
                    lines = _split_by_length(text, maybe_len)

            poems.append(
                PoemMetadata(
                    title=parsed["title"],
                    author=parsed["author"],
                    text=text,
                    lines=lines,
                    line_count=len(lines),
                    char_count=sum(len(l) for l in lines),
                )
            )
        except Exception as e:
            logger.warning(f"跳过诗歌条目: {e}")
            continue

    return poems


def load_poem_from_text(file_path: str) -> List[PoemMetadata]:
    """从TXT文件中加载诗歌

    支持格式（按空行分割，每块一首）：
    标题
    作者
    诗句
    诗句
    ...
    （空行）
    """
    poems = []
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = re.split(r"\n\s*\n", content.strip())
    for block in blocks:
        lines = block.strip().split("\n")
        lines = [l.strip() for l in lines if l.strip()]

        if not lines:
            continue

        title = lines[0] if len(lines) > 0 else "无题"
        author = lines[1] if len(lines) > 1 else "佚名"
        poem_lines = lines[2:] if len(lines) > 2 else lines

        # 如果只有两行（标题+作者），跳过
        if len(poem_lines) < 1:
            continue

        text = "".join(poem_lines)
        poems.append(
            PoemMetadata(
                title=title,
                author=author,
                text=text,
                lines=poem_lines,
                line_count=len(poem_lines),
                char_count=sum(len(l) for l in poem_lines),
            )
        )

    return poems


def load_poem_from_csv(file_path: str) -> List[PoemMetadata]:
    """从CSV文件中加载诗歌"""
    poems = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("标题") or row.get("title") or "无题"
            author = row.get("作者") or row.get("author") or "佚名"
            text = row.get("原文") or row.get("text") or row.get("content") or ""
            if not text:
                continue

            lines = extract_chinese_lines(text)
            poems.append(
                PoemMetadata(
                    title=title,
                    author=author,
                    text=text,
                    lines=lines,
                    line_count=len(lines),
                    char_count=sum(len(l) for l in lines),
                )
            )
    return poems


def load_poems_from_directory(
    directory: str, extensions: List[str] = None
) -> List[PoemMetadata]:
    """从目录加载所有诗歌"""
    extensions = extensions or [".json", ".txt", ".csv"]
    all_poems = []

    if not os.path.isdir(directory):
        raise PoemDataError(f"目录不存在: {directory}")

    for fn in sorted(os.listdir(directory)):
        fp = os.path.join(directory, fn)
        if not os.path.isfile(fp):
            continue
        ext = os.path.splitext(fn)[1].lower()
        if ext not in extensions:
            continue

        try:
            if ext == ".json":
                poems = load_poem_from_json(fp)
            elif ext == ".txt":
                poems = load_poem_from_text(fp)
            elif ext == ".csv":
                poems = load_poem_from_csv(fp)
            else:
                continue
            all_poems.extend(poems)
            logger.info(f"已加载 {fn}: {len(poems)} 首")
        except Exception as e:
            logger.warning(f"加载失败 {fn}: {e}")

    return all_poems


# ─── 内部工具 ───


def _normalize_json_input(raw: Any) -> List[dict]:
    """将各种JSON结构统一为诗歌条目列表"""
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        # 可能是 { "key": [...] }
        for val in raw.values():
            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                return [item for item in val if isinstance(item, dict)]
        # 可能是单个诗歌对象
        if any(k in raw for k in ("标题", "title", "原文", "text", "内容")):
            return [raw]
    return []


def _guess_line_length(text: str) -> int:
    """猜测诗句的字数（五言/七言）"""
    # 去掉标点
    clean = "".join(c for c in text if "一" <= c <= "鿿")
    if not clean:
        return 0

    # 尝试按5或7分割
    for try_len in (7, 5, 6, 4):
        if len(clean) % try_len == 0:
            n_segments = len(clean) // try_len
            if n_segments >= 2:
                return try_len

    # 如果非偶数，自动检测最可能的长度
    freq = {}
    for step in (5, 7):
        n = len(clean) // step
        remainder = len(clean) % step
        ratio = n / max(1, n + remainder)
        freq[step] = ratio
    return max(freq, key=freq.get) if freq else 5


def _split_by_length(text: str, char_len: int) -> List[str]:
    """按固定字数将文本分割为多句"""
    clean = "".join(c for c in text if "一" <= c <= "鿿")
    return [clean[i : i + char_len] for i in range(0, len(clean), char_len) if len(clean[i : i + char_len]) >= char_len]


def extract_poem_text(poem: PoemMetadata) -> str:
    """提取诗歌纯文本（无标点、无空格）"""
    return "".join(c for c in poem.text if "一" <= c <= "鿿")


def split_into_lines(text: str) -> List[str]:
    """将诗歌文本分割为单句"""
    return extract_chinese_lines(text)


def quick_load(text: str, title: str = "未命名", author: str = "佚名") -> PoemMetadata:
    """快速从文本创建诗歌元数据"""
    lines = extract_chinese_lines(text)
    return PoemMetadata(
        title=title,
        author=author,
        text=text,
        lines=lines,
        line_count=len(lines),
        char_count=sum(len(l) for l in lines),
    )
