# -*- coding: utf-8 -*-
"""Tests for llm_client — JSON extraction and repair with various dirty outputs."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))

from llm_client import _extract_json


def test_simple_json():
    result = _extract_json('{"key": "value"}')
    assert result == {"key": "value"}


def test_json_with_think_tag():
    result = _extract_json('<think>some reasoning</think>{"result": "ok"}')
    assert result == {"result": "ok"}


def test_json_with_code_fence():
    result = _extract_json('```json\n{"a": 1}\n```')
    assert result == {"a": 1}


def test_json_with_surrounding_text():
    result = _extract_json('这是一段解释文字 {"field": "明月", "score": 95} 后面还有文字')
    assert result == {"field": "明月", "score": 95}


def test_nested_json():
    result = _extract_json('{"outer": {"inner": [1, 2, 3]}, "name": "test"}')
    assert result == {"outer": {"inner": [1, 2, 3]}, "name": "test"}


def test_chinese_json():
    result = _extract_json('{"意象": "明月", "情感": "思乡", "作者": "李白"}')
    assert result == {"意象": "明月", "情感": "思乡", "作者": "李白"}


def test_array_json():
    result = _extract_json('[{"id": 1}, {"id": 2}]')
    assert result == [{"id": 1}, {"id": 2}]


def test_broken_json_repair():
    # Missing closing brace — repair attempts
    result = _extract_json('{"key": "value"')
    assert result is None  # unfixable single brace


def test_multiple_json_objects():
    result = _extract_json('{"a":1}\n{"b":2}')
    assert result is not None  # should extract something


def test_empty_input():
    result = _extract_json("")
    assert result is None


def test_no_json():
    result = _extract_json("这是一段纯文本，没有任何JSON")
    assert result is None


def test_boolean_and_number_types():
    result = _extract_json('{"active": true, "count": 42, "ratio": 0.95}')
    assert result == {"active": True, "count": 42, "ratio": 0.95}


def test_json_with_newlines_in_values():
    result = _extract_json('{"text": "line1\\nline2"}')
    assert result is not None


def test_deeply_nested_json():
    result = _extract_json('{"level1": {"level2": {"level3": {"key": "deep"}}}}')
    assert result == {"level1": {"level2": {"level3": {"key": "deep"}}}}


def test_json_with_unicode_escapes():
    result = _extract_json('{"char": "\\u660e\\u6708"}')
    assert result == {"char": "明月"}


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
