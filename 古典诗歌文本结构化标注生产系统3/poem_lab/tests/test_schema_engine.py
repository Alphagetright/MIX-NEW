# -*- coding: utf-8 -*-
"""Tests for schema_engine — header validation, type checking, CSV generation, edge cases."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))

from schema_engine import validate_headers, validate_output, rows_to_csv, save_template, load_template, list_templates


def test_validate_headers_valid():
    ok, msg = validate_headers([{"name": "意象", "desc": "自然意象"}, {"name": "情感", "desc": "情感类型"}])
    assert ok
    assert msg == ""


def test_validate_headers_empty():
    ok, msg = validate_headers([])
    assert not ok


def test_validate_headers_duplicate():
    ok, msg = validate_headers([{"name": "意象"}, {"name": "意象"}])
    assert not ok
    assert "重复" in msg


def test_validate_headers_illegal_chars():
    ok, msg = validate_headers([{"name": "意,象"}])
    assert not ok
    assert "非法字符" in msg


def test_validate_output_valid():
    cm = [{"header": "意象名称", "field": "imagery", "data_type": "string"}]
    ok, issues = validate_output({"imagery": "明月"}, cm)
    assert ok
    assert len(issues) == 0


def test_validate_output_missing_field():
    cm = [{"header": "意象", "field": "imagery"}, {"header": "情感", "field": "sentiment"}]
    ok, issues = validate_output({"imagery": "明月"}, cm)
    assert not ok
    assert any("sentiment" in i or "情感" in i for i in issues)


def test_validate_output_enum():
    cm = [{"header": "情感", "field": "sentiment", "data_type": "enum", "enum_values": ["喜悦", "悲伤"]}]
    ok, _ = validate_output({"sentiment": "喜悦"}, cm)
    assert ok
    ok, _ = validate_output({"sentiment": "愤怒"}, cm)
    assert not ok


def test_validate_output_type_int():
    cm = [{"header": "频次", "field": "count", "data_type": "int"}]
    ok, _ = validate_output({"count": 5}, cm)
    assert ok
    ok, _ = validate_output({"count": "abc"}, cm)
    assert not ok


def test_rows_to_csv():
    cm = [{"header": "意象", "field": "imagery"}, {"header": "情感", "field": "sentiment"}]
    rows = [{"imagery": "明月", "sentiment": "思乡"}, {"imagery": "梅花", "sentiment": "高洁"}]
    csv = rows_to_csv(rows, cm)
    assert "明月" in csv
    assert "思乡" in csv
    assert csv.count("\n") >= 2


def test_rows_to_csv_empty():
    csv = rows_to_csv([], [])
    assert csv == ""


def test_rows_to_csv_special_chars():
    cm = [{"header": "原文", "field": "text"}]
    rows = [{"text": '他说："你好"'}]
    csv = rows_to_csv(rows, cm)
    assert '""你好""' in csv  # double quotes escaped in CSV


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
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
