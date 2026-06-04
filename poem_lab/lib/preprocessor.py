# -*- coding: utf-8 -*-
"""古典诗歌文本预处理 — 清洗、归一化、去重、格式转换"""
import re
from collections import Counter

FULL_TO_HALF = str.maketrans(
    '０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ',
    '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
)

VARIANT_CHARS = {
    '羣': '群', '峯': '峰', '邨': '村', '峩': '峨', '喫': '吃',
    '卻': '却', '閒': '闲', '棲': '栖', '煙': '烟', '簾': '帘',
    '鑑': '鉴', '鍾': '钟', '巖': '岩', '廻': '回', '徧': '遍',
    '爲': '为', '卽': '即', '旣': '既', '槩': '概', '氷': '冰',
    '淚': '泪', '爭': '争', '畧': '略', '眞': '真', '着': '著',
    '竝': '并', '羣': '群', '昇': '升', '災': '灾', '牀': '床',
}


def normalize_text(text: str) -> str:
    """全角转半角 + 异体字归一化 + 多余空白清理"""
    text = text.translate(FULL_TO_HALF)
    for variant, standard in VARIANT_CHARS.items():
        text = text.replace(variant, standard)
    text = re.sub(r'[ \t]+', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def normalize_punctuation(text: str) -> str:
    """统一中文标点符号"""
    replacements = {
        ',': '，', ';': '；', ':': '：', '!': '！', '?': '？',
        '(': '（', ')': '）', '[': '「', ']': '」',
        '．．．': '……', '...': '……', '。。': '。',
        '、、': '、', '，，': '，', '；；': '；',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def deduplicate_poems(poems: list) -> tuple:
    """按标题+作者去重，返回(去重后列表, 重复项列表)"""
    seen = {}
    duplicates = []
    unique = []
    for p in poems:
        key = (p.get('标题', '').strip(), p.get('作者', '').strip())
        if key in seen:
            duplicates.append(p)
        else:
            seen[key] = True
            unique.append(p)
    return unique, duplicates


def deduplicate_lines(text: str) -> str:
    """删除诗中的完全重复行"""
    lines = text.split('\n')
    seen = set()
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped and stripped not in seen:
            seen.add(stripped)
            result.append(line)
        elif not stripped:
            result.append(line)
    return '\n'.join(result)


def detect_encoding_issues(text: str) -> list:
    """检测文本中的编码问题"""
    issues = []
    if '�' in text:
        issues.append('存在Unicode替换字符(�)，原始文件可能编码错误')
    if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', text):
        issues.append('存在不可打印控制字符')
    if re.search(r'[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]', text):
        issues.append('存在拼音标注字符，建议清理')
    return issues


def validate_poem_structure(poem: dict) -> list:
    """校验单首诗的结构完整性"""
    issues = []
    if not poem.get('原文', '').strip():
        issues.append('原文为空')
        return issues
    if not poem.get('标题', '').strip():
        issues.append('标题为空')
    text = poem.get('原文', '')
    char_count = len(re.sub(r'[，。！？、；：\s]', '', text))
    if char_count < 4:
        issues.append(f'原文过短（{char_count}字），可能不完整')
    if char_count > 2000:
        issues.append(f'原文过长（{char_count}字），可能非单首诗')
    line_count = len([l for l in text.split('\n') if l.strip()])
    if line_count == 1 and char_count > 40:
        issues.append('原文仅一行但字数较多，建议检查换行格式')
    return issues


def batch_validate(poems: list) -> dict:
    """批量校验诗歌列表，返回统计和问题清单"""
    stats = {'total': len(poems), 'valid': 0, 'with_issues': 0, 'issues': []}
    for i, p in enumerate(poems):
        poem_issues = validate_poem_structure(p)
        if poem_issues:
            stats['with_issues'] += 1
            for issue in poem_issues:
                stats['issues'].append({
                    'index': i, '编号': p.get('编号', ''),
                    '标题': p.get('标题', ''), '问题': issue
                })
        else:
            stats['valid'] += 1
    return stats


def split_by_dynasty(poems: list) -> dict:
    """按朝代分组"""
    groups = {}
    for p in poems:
        dynasty = p.get('朝代', '未知').strip() or '未知'
        groups.setdefault(dynasty, []).append(p)
    return groups


def split_by_author(poems: list) -> dict:
    """按作者分组"""
    groups = {}
    for p in poems:
        author = p.get('作者', '未知').strip() or '未知'
        groups.setdefault(author, []).append(p)
    return groups


def extract_keywords(text: str, top_n: int = 10) -> list:
    """从诗中提取关键词（基于字频和位置权重）"""
    clean = re.sub(r'[，。！？、；：""''《》\s,.!?;:\'\"()（）\[\]「」]', '', text)
    counter = Counter()
    for i, char in enumerate(clean):
        position_weight = 1.0 + (1.0 - i / max(len(clean), 1)) * 0.5
        counter[char] += position_weight
    return counter.most_common(top_n)


def count_lines_and_chars(text: str) -> dict:
    """统计诗歌的行数和字数"""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    total_chars = sum(len(re.sub(r'[，。！？、；：\s]', '', l)) for l in lines)
    return {
        "行数": len(lines),
        "总字数": total_chars,
        "平均每行字数": round(total_chars / max(len(lines), 1), 1),
        "最长行字数": max((len(re.sub(r'[，。！？、；：\s]', '', l)) for l in lines), default=0)
    }


def estimate_reading_level(text: str) -> dict:
    """估算诗歌的阅读难度"""
    clean = re.sub(r'[，。！？、；：\s]', '', text)
    char_count = len(clean)

    rare_chars = sum(1 for c in clean if ord(c) > 0x9FFF or (0x3400 <= ord(c) <= 0x4DBF))
    rare_ratio = rare_chars / max(char_count, 1)

    if char_count <= 20:
        length_level = '短'
    elif char_count <= 56:
        length_level = '中'
    else:
        length_level = '长'

    if rare_ratio < 0.02:
        vocab_level = '常用'
    elif rare_ratio < 0.08:
        vocab_level = '一般'
    else:
        vocab_level = '生僻'

    return {
        '字数': char_count,
        '长度等级': length_level,
        '生僻字比例': round(rare_ratio * 100, 1),
        '词汇等级': vocab_level,
        '整体难度': '容易' if length_level == '短' and vocab_level == '常用' else
                    '困难' if length_level == '长' or vocab_level == '生僻' else '中等'
    }
