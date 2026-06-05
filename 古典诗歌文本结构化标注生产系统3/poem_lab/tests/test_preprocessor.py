# -*- coding: utf-8 -*-
"""Tests for preprocessor — normalization, dedup, validation, reading level."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))

from preprocessor import (normalize_text, normalize_punctuation, deduplicate_poems,
                           deduplicate_lines, detect_encoding_issues, validate_poem_structure,
                           batch_validate, split_by_dynasty, split_by_author,
                           extract_keywords, estimate_reading_level)


def test_normalize_fullwidth():
    result = normalize_text('１２３ＡＢＣ')
    assert '123ABC' in result


def test_normalize_variant_chars():
    result = normalize_text('羣峯')
    assert '群' in result or '峰' in result


def test_normalize_whitespace():
    result = normalize_text('床前  明月光')
    assert '  ' not in result or result == '床前明月光'


def test_normalize_punctuation_comma():
    result = normalize_punctuation('hello, world')
    assert '，' in result


def test_normalize_punctuation_semicolon():
    result = normalize_punctuation('a; b')
    assert '；' in result


def test_deduplicate_poems():
    poems = [
        {'标题': '静夜思', '作者': '李白', '原文': 'text1'},
        {'标题': '静夜思', '作者': '李白', '原文': 'text2'},
        {'标题': '春望', '作者': '杜甫', '原文': 'text3'},
    ]
    unique, dups = deduplicate_poems(poems)
    assert len(unique) == 2
    assert len(dups) == 1


def test_deduplicate_poems_none():
    poems = [{'标题': 'A', '作者': 'X', '原文': 't1'}, {'标题': 'B', '作者': 'Y', '原文': 't2'}]
    unique, dups = deduplicate_poems(poems)
    assert len(unique) == 2
    assert len(dups) == 0


def test_detect_encoding_issues_clean():
    issues = detect_encoding_issues('床前明月光')
    assert len(issues) == 0


def test_detect_encoding_issues_replacement_char():
    issues = detect_encoding_issues('床前�月光')
    assert len(issues) > 0


def test_validate_poem_valid():
    issues = validate_poem_structure({'标题': '静夜思', '原文': '床前明月光，疑是地上霜。举头望明月，低头思故乡。'})
    assert len(issues) == 0


def test_validate_poem_empty_text():
    issues = validate_poem_structure({'标题': 'Test', '原文': ''})
    assert len(issues) > 0
    assert any('原文为空' in i for i in issues)


def test_validate_poem_too_short():
    issues = validate_poem_structure({'标题': 'Test', '原文': '床前'})
    assert any('过短' in i for i in issues)


def test_batch_validate():
    poems = [
        {'编号': 'P01', '标题': 'A', '原文': '床前明月光，疑是地上霜。'},
        {'编号': 'P02', '标题': 'B', '原文': ''},
    ]
    result = batch_validate(poems)
    assert result['total'] == 2
    assert result['with_issues'] >= 1


def test_split_by_dynasty():
    poems = [
        {'朝代': '唐', '原文': 'a'},
        {'朝代': '唐', '原文': 'b'},
        {'朝代': '宋', '原文': 'c'},
    ]
    groups = split_by_dynasty(poems)
    assert len(groups['唐']) == 2
    assert len(groups['宋']) == 1


def test_split_by_author():
    poems = [
        {'作者': '李白', '原文': 'a'},
        {'作者': '杜甫', '原文': 'b'},
        {'作者': '李白', '原文': 'c'},
    ]
    groups = split_by_author(poems)
    assert len(groups['李白']) == 2
    assert len(groups['杜甫']) == 1


def test_extract_keywords():
    kw = extract_keywords('床前明月光疑是地上霜举头望明月低头思故乡')
    assert len(kw) > 0
    assert kw[0][0] in '床前明月光疑是地上霜举头望低思故乡'


def test_estimate_reading_level_short():
    level = estimate_reading_level('床前明月光')
    assert level['字数'] > 0
    assert '长度等级' in level
    assert '整体难度' in level


def test_estimate_reading_level_long():
    long_text = '床前明月光疑是地上霜举头望明月低头思故乡' * 3
    level = estimate_reading_level(long_text)
    assert level['长度等级'] in ('中', '长')


def test_deduplicate_lines():
    text = '床前明月光\n床前明月光\n疑是地上霜'
    result = deduplicate_lines(text)
    assert result.count('床前明月光') == 1


def test_normalize_mixed_text():
    result = normalize_text('床前　明月光\n\n\n疑是地上霜')
    assert '明月光' in result
    assert result.count('\n') <= 2


def test_detect_encoding_issues_control_chars():
    issues = detect_encoding_issues('test\x00text')
    assert len(issues) > 0


def test_validate_poem_no_title():
    issues = validate_poem_structure({'标题': '', '原文': '床前明月光，疑是地上霜。举头望明月，低头思故乡。'})
    assert any('标题为空' in i for i in issues)


def test_batch_validate_all_valid():
    poems = [
        {'编号': 'P01', '标题': '静夜思', '原文': '床前明月光，疑是地上霜。举头望明月，低头思故乡。'},
        {'编号': 'P02', '标题': '春望', '原文': '国破山河在，城春草木深。感时花溅泪，恨别鸟惊心。'},
    ]
    result = batch_validate(poems)
    assert result['valid'] == 2


def test_split_by_dynasty_unknown():
    poems = [{'原文': 'test1'}, {'原文': 'test2'}]
    groups = split_by_dynasty(poems)
    assert '未知' in groups


def test_estimate_reading_level_rare_chars():
    level = estimate_reading_level('㐀㐁㐂床前明月光')
    assert level['词汇等级'] == '生僻'


def test_extract_keywords_single_char():
    kw = extract_keywords('明月明')
    assert len(kw) > 0


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
