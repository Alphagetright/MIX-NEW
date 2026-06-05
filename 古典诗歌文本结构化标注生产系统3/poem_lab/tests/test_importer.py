# -*- coding: utf-8 -*-
"""Tests for poem parsing — multi-format import, edge cases, invalid input."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))

import json, csv, io

# Mirror the _parse_poems logic from app.py
import re

def _parse_poems(text: str) -> list:
    poems = []
    blocks = re.split(r'\n\s*\n', text.strip())
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        poem = {"编号": "", "标题": "", "作者": "", "朝代": "", "原文": ""}
        kv = re.findall(r'(?:^|\n)(编号|标题|作者|朝代|原文)[：:]\s*(.*?)(?=\n(?:编号|标题|作者|朝代|原文)[：:]|\Z)', block, re.DOTALL)
        if kv:
            for k, v in kv:
                poem[k] = v.strip()
        else:
            m = re.match(r'[《「](.+?)[》」]\s*(.+)', block)
            if m:
                poem["标题"] = m.group(1).strip()
                rest = m.group(2).strip()
                for sep in ['\n', '  ', '  ']:
                    if sep in rest:
                        poem["作者"] = rest[:rest.index(sep)].strip()
                        poem["原文"] = rest[rest.index(sep):].strip()
                        break
                if not poem["原文"]:
                    poem["原文"] = rest
            else:
                poem["原文"] = block

        if poem["原文"]:
            poems.append(poem)

    for i, p in enumerate(poems):
        if not p["编号"]:
            p["编号"] = f"P{i+1:03d}"
    return poems


def test_kv_format():
    text = "编号：P001\n标题：静夜思\n作者：李白\n原文：\n床前明月光，疑是地上霜。"
    poems = _parse_poems(text)
    assert len(poems) == 1
    assert poems[0]["标题"] == "静夜思"
    assert poems[0]["作者"] == "李白"


def test_book_title_format():
    text = "《静夜思》李白\n床前明月光，疑是地上霜。举头望明月，低头思故乡。"
    poems = _parse_poems(text)
    assert len(poems) == 1
    assert poems[0]["标题"] == "静夜思"


def test_multiple_poems():
    text = "《静夜思》李白\n床前明月光\n\n《春望》杜甫\n国破山河在"
    poems = _parse_poems(text)
    assert len(poems) == 2
    assert poems[1]["标题"] == "春望"


def test_auto_numbering():
    text = "床前明月光\n\n疑是地上霜"
    poems = _parse_poems(text)
    assert poems[0]["编号"] == "P001"
    assert poems[1]["编号"] == "P002"


def test_empty_input():
    poems = _parse_poems("")
    assert poems == []


def test_whitespace_only():
    poems = _parse_poems("   \n\n  \n  ")
    assert poems == []


def test_no_content_line():
    poems = _parse_poems("标题：test\n作者：someone")
    assert poems == []  # no 原文 field


def test_single_line_poem():
    text = "春眠不觉晓，处处闻啼鸟。"
    poems = _parse_poems(text)
    assert len(poems) == 1
    assert poems[0]["编号"] == "P001"


def test_mixed_formats():
    text = "编号：P01\n标题：诗A\n原文：\n床前明月光\n\n《诗B》作者B\n疑是地上霜"
    poems = _parse_poems(text)
    assert len(poems) == 2


def test_poem_with_dynasty():
    text = "编号：P001\n标题：静夜思\n作者：李白\n朝代：唐\n原文：\n床前明月光"
    poems = _parse_poems(text)
    assert poems[0]["朝代"] == "唐"


def run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR {t.__name__}: {e}")
    print(f"\n  {passed} passed, {failed} failed, {len(tests)} total")
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
