# -*- coding: utf-8 -*-
"""标注辅助工具集 — 唐诗意象词库、用典检测、情感极性、词频分析"""
import re
from collections import Counter

# ── 唐诗常见意象词库（200+）──
IMAGERY_LEXICON = {
    "自然-天象": ["明月", "星辰", "白日", "夕阳", "残阳", "落霞", "朝霞", "浮云", "白云", "青云",
                "彩云", "彤云", "乌云", "烟云", "风雪", "霜雪", "朝露", "白露", "寒露", "清霜",
                "春风", "秋风", "东风", "西风", "朔风", "寒风", "和风", "细雨", "暴雨", "晴空"],
    "自然-山水": ["青山", "绿水", "碧水", "沧海", "江河", "流水", "溪流", "瀑布", "深潭",
                "孤峰", "群峰", "远山", "空山", "寒山", "翠微", "烟波", "湖光", "清泉"],
    "自然-花木": ["落花", "飞花", "残花", "梅花", "菊花", "桃花", "荷花", "莲花", "牡丹",
                "杨柳", "垂杨", "松柏", "翠竹", "青松", "梧桐", "芭蕉", "芳草", "枯藤",
                "红叶", "落叶", "青苔", "幽兰", "桂树", "桑麻"],
    "自然-鸟兽": ["白鹭", "黄鹂", "燕子", "鸿雁", "归雁", "孤鸿", "杜鹃", "啼鹃", "子规",
                "猿猴", "哀猿", "骏马", "老马", "青鸟", "沙鸥", "寒鸦", "凤凰", "蝴蝶"],
    "人文-建筑": ["孤城", "古城", "长亭", "短亭", "客舍", "驿馆", "楼台", "高阁",
                "玉阶", "雕栏", "珠帘", "绮窗", "朱门", "柴门", "庭院", "深宫",
                "寺庙", "僧舍", "草堂", "茅屋", "断桥", "古道", "长阶"],
    "人文-器物": ["酒杯", "金樽", "玉壶", "银烛", "铜镜", "宝剑", "长铗", "孤舟",
                "扁舟", "征帆", "画船", "青灯", "素琴", "羌笛", "玉笛", "琵琶",
                "锦瑟", "罗衣", "霓裳", "珠翠", "玉簪", "金钗"],
    "人文-地点": ["长安", "洛阳", "金陵", "扬州", "边塞", "阳关", "玉门", "塞外",
                "江南", "巴蜀", "潇湘", "楚地", "燕地", "吴宫", "咸阳", "凉州",
                "天山", "轮台", "楼兰", "阴山", "陇西", "江东"]
}

# 情感极性词
SENTIMENT_WORDS = {
    "positive": ["乐", "喜", "笑", "欢", "悦", "欣", "畅", "怡", "快", "逸", "豪", "壮",
              "闲", "悠", "安", "宁", "暖", "明", "清", "芳", "秀", "丽", "朗"],
    "negative": ["悲", "愁", "哀", "伤", "苦", "恨", "怨", "忧", "戚", "凄", "凉", "寒",
              "孤", "独", "寂", "寞", "断", "残", "落", "凋", "枯", "败", "绝"],
    "ambiguous": ["思", "忆", "怀", "念", "叹", "感", "望", "梦", "寄", "问", "怜", "怅"]
}


def detect_imagery(text: str) -> list:
    """检测诗歌中的意象词汇，返回 [(意象词, 类别), ...]"""
    found = []
    for category, words in IMAGERY_LEXICON.items():
        for w in words:
            if w in text:
                found.append({"word": w, "category": category})
    return found


def detect_allusions(text: str) -> list:
    """检测诗歌中可能的用典（基于古籍常见典故关键词）"""
    ALLUSION_PATTERNS = [
        ("庄周梦蝶", ["庄周", "蝴蝶梦", "梦蝶"]),
        ("屈原投江", ["屈子", "汨罗", "离骚", "楚臣"]),
        ("陶渊明归隐", ["五柳", "东篱", "采菊", "桃源", "归去来"]),
        ("昭君出塞", ["昭君", "明妃", "青冢"]),
        ("荆轲刺秦", ["荆轲", "易水", "击筑"]),
        ("贾谊贬谪", ["贾生", "贾谊", "长沙傅"]),
        ("司马相如", ["长卿", "子虚", "上林", "凤求凰"]),
        ("王谢世家", ["王谢", "乌衣巷", "堂前燕"]),
        ("垓下之围", ["项羽", "霸王", "垓下", "虞姬"]),
        ("铜雀台", ["铜雀", "二乔", "东风不与"]),
        ("赤壁之战", ["赤壁", "周郎", "东风", "借箭"]),
        ("卧薪尝胆", ["勾践", "卧薪", "尝胆", "夫差"]),
        ("伯牙子期", ["伯牙", "子期", "知音", "高山流水"]),
        ("嫦娥奔月", ["嫦娥", "广寒", "玉兔"]),
        ("牛郎织女", ["牛郎", "织女", "七夕", "鹊桥", "银河"]),
    ]
    found = []
    for name, keywords in ALLUSION_PATTERNS:
        for kw in keywords:
            if kw in text:
                found.append({"allusion": name, "matched_keyword": kw, "confidence": "medium"})
                break
    return found


def sentiment_polarity(text: str) -> dict:
    """基于关键词规则快速推断情感极性（不依赖 LLM）"""
    pos_score = sum(1 for c in text if c in SENTIMENT_WORDS["positive"])
    neg_score = sum(1 for c in text if c in SENTIMENT_WORDS["negative"])
    amb_score = sum(1 for c in text if c in SENTIMENT_WORDS["ambiguous"])

    total = pos_score + neg_score + amb_score
    if total == 0:
        return {"primary": "neutral", "confidence": "low", "detail": {"positive": 0, "negative": 0, "ambiguous": 0}}

    if pos_score > neg_score * 1.5:
        primary = "positive"
    elif neg_score > pos_score * 1.5:
        primary = "negative"
    elif pos_score > neg_score:
        primary = "positive_tending"
    elif neg_score > pos_score:
        primary = "negative_tending"
    else:
        primary = "balanced"

    return {
        "primary": primary,
        "confidence": "high" if total >= 4 else "medium" if total >= 2 else "low",
        "detail": {"positive": pos_score, "negative": neg_score, "ambiguous": amb_score}
    }


def word_frequency(poems: list, top_n: int = 50) -> list:
    """统计诗歌语料的词频 Top-N"""
    counter = Counter()
    for p in poems:
        text = p.get("原文", "") + p.get("标题", "")
        chars = re.sub(r'[，。！？、；：""''《》\s,.!?;:\'\"()（）\[\]「」]', '', text)
        for c in chars:
            counter[c] += 1
    return counter.most_common(top_n)


def character_frequency_by_author(poems: list, author: str, top_n: int = 20) -> list:
    """按作者统计用字频率"""
    counter = Counter()
    for p in poems:
        if p.get("作者", "") == author:
            text = p.get("原文", "")
            chars = re.sub(r'[，。！？、；：""''《》\s,.!?;\'\"()（）\[\]「」]', '', text)
            for c in chars:
                counter[c] += 1
    return counter.most_common(top_n)


def imagery_cooccurrence(poems: list, target_word: str, top_n: int = 20) -> list:
    """分析指定意象词与其他词的共现关系"""
    from collections import Counter
    cooccur = Counter()
    for p in poems:
        text = p.get("原文", "")
        if target_word in text:
            chars = re.sub(r'[，。！？、；：""''《》\s,.!?;:\'\"()（）\[\]「」]', '', text)
            for c in chars:
                if c != target_word:
                    cooccur[c] += 1
    return cooccur.most_common(top_n)


def author_style_fingerprint(poems: list, author: str) -> dict:
    """构建诗人的风格指纹"""
    author_poems = [p for p in poems if p.get("作者", "") == author]
    if not author_poems:
        return {"error": f"未找到作者 {author} 的作品"}

    all_chars = Counter()
    imagery_counter = Counter()
    sentiment_counter = Counter()
    total_chars = 0

    for p in author_poems:
        text = p.get("原文", "")
        chars = re.sub(r'[，。！？、；：""''《》\s,.!?;:\'\"()（）\[\]「」]', '', text)
        total_chars += len(chars)
        for c in chars:
            all_chars[c] += 1

        # Detect imagery
        for img in detect_imagery(text):
            imagery_counter[img["word"]] += 1

        # Sentiment
        pol = sentiment_polarity(text)
        sentiment_counter[pol["primary"]] += 1

    return {
        "作者": author,
        "作品数": len(author_poems),
        "总字数": total_chars,
        "高频字Top10": all_chars.most_common(10),
        "常用意象Top10": imagery_counter.most_common(10),
        "情感倾向分布": dict(sentiment_counter.most_common()),
        "平均单首字数": round(total_chars / max(len(author_poems), 1)),
        "用字多样性": round(len(all_chars) / max(total_chars, 1) * 100, 1)
    }


def compare_authors(poems: list, author_a: str, author_b: str) -> dict:
    """对比两位诗人的风格差异"""
    fp_a = author_style_fingerprint(poems, author_a)
    fp_b = author_style_fingerprint(poems, author_b)

    chars_a = set(c for c, _ in fp_a.get("高频字Top10", []))
    chars_b = set(c for c, _ in fp_b.get("高频字Top10", []))
    shared_chars = chars_a & chars_b
    unique_a = chars_a - chars_b
    unique_b = chars_b - chars_a

    return {
        "作者A": {"名": author_a, "作品数": fp_a.get("作品数", 0), "平均字数": fp_a.get("平均单首字数", 0), "用字多样性": fp_a.get("用字多样性", 0)},
        "作者B": {"名": author_b, "作品数": fp_b.get("作品数", 0), "平均字数": fp_b.get("平均单首字数", 0), "用字多样性": fp_b.get("用字多样性", 0)},
        "高频字对比": {"共用字": list(shared_chars), f"{author_a}独有": list(unique_a), f"{author_b}独有": list(unique_b)},
        "情感倾向对比": {"A": fp_a.get("情感倾向分布", {}), "B": fp_b.get("情感倾向分布", {})}
    }


def extract_rhyme_pattern(text: str) -> dict:
    """简易押韵模式检测（基于现代拼音）"""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if len(lines) < 2:
        return {"error": "行数不足"}

    endings = []
    for line in lines:
        clean = re.sub(r'[，。！？、；：""''《》\s,.!?;:\'\"()（）\[\]「」]', '', line)
        endings.append(clean[-1] if clean else '')

    pattern = {}
    for i, end_char in enumerate(endings):
        pattern.setdefault(end_char, []).append(i + 1)

    rhyme_scheme = []
    for end_char, positions in pattern.items():
        if len(positions) >= 2:
            rhyme_scheme.append({"韵字": end_char, "位置（句号）": positions, "频次": len(positions)})

    return {
        "总行数": len(lines),
        "句末字": endings,
        "韵脚": rhyme_scheme,
        "押韵类型": "一韵到底" if len(rhyme_scheme) <= 1 else "换韵" if len(rhyme_scheme) >= 3 else "宽松用韵"
    }


METER_PATTERNS = {
    "五言": [
        {"name": "仄仄平平仄", "pattern": "仄仄平平仄", "example": "国破山河在"},
        {"name": "平平仄仄平", "pattern": "平平仄仄平", "example": "城春草木深"},
        {"name": "平平平仄仄", "pattern": "平平平仄仄", "example": "感时花溅泪"},
        {"name": "仄仄仄平平", "pattern": "仄仄仄平平", "example": "恨别鸟惊心"},
    ],
    "七言": [
        {"name": "平平仄仄平平仄", "pattern": "平平仄仄平平仄", "example": "两个黄鹂鸣翠柳"},
        {"name": "仄仄平平仄仄平", "pattern": "仄仄平平仄仄平", "example": "一行白鹭上青天"},
    ]
}


def detect_meter_type(line: str) -> dict:
    """检测诗句的基本平仄类型"""
    clean = re.sub(r'[，。！？、；：""''《》\s,.!?;:\'\"()（）\[\]「」]', '', line)
    length = len(clean)
    return {
        "原文": line.strip(),
        "字数": length,
        "可能诗体": "五言" if length == 5 else "七言" if length == 7 else f"杂言({length}字)"
    }


def imagery_evolution_stats(poems: list, imagery_word: str) -> list:
    """追踪特定意象的历时演变"""
    timeline = []
    for p in poems:
        if imagery_word in p.get("原文", ""):
            timeline.append({
                "标题": p.get("标题", ""),
                "作者": p.get("作者", ""),
                "朝代": p.get("朝代", ""),
                "原文": p.get("原文", "")[:60]
            })
    by_dynasty = {}
    for item in timeline:
        d = item["朝代"] or "未知"
        by_dynasty.setdefault(d, []).append(item)
    return [{"dynasty": d, "count": len(items), "samples": items[:3]} for d, items in by_dynasty.items()]
