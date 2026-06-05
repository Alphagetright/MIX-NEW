# -*- coding: utf-8 -*-
"""Tests for annotation_tools — imagery, allusions, sentiment, word freq, style."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))

from annotation_tools import (detect_imagery, detect_allusions, sentiment_polarity,
                               word_frequency, character_frequency_by_author,
                               imagery_cooccurrence, author_style_fingerprint,
                               compare_authors, extract_rhyme_pattern, detect_meter_type)


def test_detect_imagery_moonlight():
    results = detect_imagery('床前明月光，疑是地上霜')
    assert len(results) > 0
    words = [r['word'] for r in results]
    assert any('明' in w or '月' in w for w in words)


def test_detect_imagery_empty():
    results = detect_imagery('')
    assert results == []


def test_detect_imagery_multiple():
    results = detect_imagery('明月松间照，清泉石上流。竹喧归浣女，莲动下渔舟。')
    assert len(results) >= 2


def test_detect_allusions_zhuangzhou():
    results = detect_allusions('庄周梦蝶，望帝春心托杜鹃')
    assert len(results) >= 1
    assert any('庄周' in r.get('allusion', '') for r in results)


def test_detect_allusions_none():
    results = detect_allusions('床前明月光')
    assert len(results) == 0


def test_sentiment_positive():
    result = sentiment_polarity('两个黄鹂鸣翠柳，一行白鹭上青天。窗含西岭千秋雪，门泊东吴万里船。')
    assert result['primary'] in ('positive', 'positive_tending', 'neutral')


def test_sentiment_negative():
    result = sentiment_polarity('国破山河在，城春草木深。感时花溅泪，恨别鸟惊心。')
    assert result['primary'] in ('negative', 'negative_tending', 'balanced')


def test_sentiment_neutral():
    result = sentiment_polarity('一二三四五六七')
    assert result['primary'] == 'neutral'


def test_word_frequency():
    poems = [{'标题': 'A', '原文': '床前明月光'}, {'标题': 'B', '原文': '床前明月光'}]
    freq = word_frequency(poems, top_n=5)
    assert len(freq) > 0
    assert freq[0][1] >= 2


def test_word_frequency_empty():
    freq = word_frequency([], top_n=5)
    assert freq == []


def test_character_frequency_by_author():
    poems = [
        {'作者': '李白', '原文': '床前明月光'},
        {'作者': '杜甫', '原文': '国破山河在'},
    ]
    freq = character_frequency_by_author(poems, '李白', top_n=5)
    assert len(freq) > 0


def test_character_frequency_unknown_author():
    freq = character_frequency_by_author([], 'Unknown', top_n=5)
    assert freq == []


def test_imagery_cooccurrence():
    poems = [
        {'原文': '床前明月光疑是地上霜'},
        {'原文': '举头望明月低头思故乡'},
    ]
    result = imagery_cooccurrence(poems, '明')
    assert len(result) > 0


def test_author_style_fingerprint():
    poems = [
        {'作者': '李白', '原文': '床前明月光疑是地上霜'},
        {'作者': '李白', '原文': '举头望明月低头思故乡'},
    ]
    fp = author_style_fingerprint(poems, '李白')
    assert fp['作品数'] == 2
    assert fp['总字数'] > 0


def test_author_style_fingerprint_unknown():
    fp = author_style_fingerprint([], 'Unknown')
    assert 'error' in fp


def test_compare_authors():
    poems = [
        {'作者': '李白', '朝代': '唐', '原文': '床前明月光'},
        {'作者': '杜甫', '朝代': '唐', '原文': '国破山河在'},
    ]
    result = compare_authors(poems, '李白', '杜甫')
    assert '作者A' in result
    assert '作者B' in result


def test_extract_rhyme_pattern_five_char():
    result = extract_rhyme_pattern('床前明月光\n疑是地上霜\n举头望明月\n低头思故乡')
    assert result['总行数'] == 4


def test_extract_rhyme_pattern_single_line():
    result = extract_rhyme_pattern('床前明月光')
    assert 'error' in result


def test_detect_meter_five():
    result = detect_meter_type('床前明月光')
    assert result['字数'] == 5
    assert '五言' in result.get('可能诗体', '')


def test_detect_meter_seven():
    result = detect_meter_type('两个黄鹂鸣翠柳')
    assert result['字数'] == 7


def test_detect_meter_other():
    result = detect_meter_type('床前明月光疑是地上霜')
    assert result['字数'] > 7
    assert '杂言' in result.get('可能诗体', '')


def test_sentiment_with_ambiguous():
    result = sentiment_polarity('思君不见君，望月空叹息')
    assert result['primary'] in ('positive', 'negative', 'positive_tending', 'negative_tending', 'balanced', 'neutral')
    assert 'confidence' in result


def test_imagery_cooccurrence_empty():
    result = imagery_cooccurrence([], '明月')
    assert result == []


def test_rhyme_pattern_empty_text():
    result = extract_rhyme_pattern('')
    assert 'error' in result


def test_detect_allusions_multiple():
    text = '庄周梦蝶心茫然，欲效陶潜归去来。易水萧萧西风冷，满座衣冠似雪。'
    results = detect_allusions(text)
    assert len(results) >= 2


def test_word_frequency_top_limit():
    poems = [{'原文': '床前明月光'}, {'原文': '疑是地上霜'}, {'原文': '举头望明月'}]
    freq = word_frequency(poems, top_n=3)
    assert len(freq) <= 3


def test_seven_character_meter():
    result = detect_meter_type('一行白鹭上青天')
    assert result['字数'] == 7


def test_detect_imagery_water():
    results = detect_imagery('飞流直下三千尺，疑是银河落九天。')
    assert len(results) >= 1


def test_compare_authors_same_dynasty():
    poems = [
        {'作者': '王维', '朝代': '唐', '原文': '空山新雨后'},
        {'作者': '孟浩然', '朝代': '唐', '原文': '春眠不觉晓'},
    ]
    result = compare_authors(poems, '王维', '孟浩然')
    assert '高频字对比' in result


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
