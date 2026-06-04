# -*- coding: utf-8 -*-
"""元数据猜测 —— 标题、作者、体裁识别"""

import re


class TitleGuesser:
    """标题识别"""

    def __init__(self):
        self._patterns = [
            r"^《(.+)》$",
            r"^「(.+)」$",
            r"^【(.+)】$",
            r"^[○●◆◇]*(.+)[○●◆◇]*$",
        ]

    def guess(self, line):
        for pattern in self._patterns:
            match = re.match(pattern, line.strip())
            if match:
                return match.group(1)
        if len(line.strip()) <= 20 and not re.search(r"[，。！？；]", line):
            return line.strip()
        return None

    def is_title(self, line):
        for pattern in self._patterns:
            if re.search(pattern, line.strip()):
                return True
        if len(line.strip()) <= 15 and not re.search(r"[，。！？]", line):
            return True
        return False


class AuthorGuesser:
    """作者识别"""

    def __init__(self):
        self._markers = [
            "作者", "作者：", "作者:", "文/", "文：",
            "by", "By",
        ]
        self._known_authors = [
            "李白", "杜甫", "王维", "白居易", "李商隐", "杜牧",
            "王之涣", "王昌龄", "孟浩然", "韦应物", "刘禹锡",
            "韩愈", "柳宗元", "元稹", "张九龄", "岑参", "高适",
            "苏轼", "辛弃疾", "李清照", "陆游", "王安石",
        ]

    def guess(self, line):
        for marker in self._markers:
            if marker in line:
                candidate = line.split(marker)[-1].strip()
                candidate = re.sub(r"[：:：\s]", "", candidate)
                if candidate:
                    return candidate
        for author in self._known_authors:
            if author in line and len(line) < 30:
                return author
        return None


class GenreGuesser:
    """体裁猜测"""

    def __init__(self):
        self._keywords = {
            "五绝": ["五绝", "五言绝句"],
            "七绝": ["七绝", "七言绝句"],
            "五律": ["五律", "五言律诗"],
            "七律": ["七律", "七言律诗"],
            "排律": ["排律"],
            "古风": ["古风", "古体诗"],
            "词": ["词牌", "浣溪沙", "菩萨蛮", "蝶恋花", "念奴娇"],
        }

    def guess(self, text):
        for genre, keywords in self._keywords.items():
            for kw in keywords:
                if kw in text:
                    return genre
        return None

    def guess_from_lines(self, lines):
        if not lines:
            return None
        first_line_len = len(lines[0])
        line_count = len(lines)
        if line_count == 4:
            if first_line_len == 5:
                return "五绝"
            elif first_line_len == 7:
                return "七绝"
        elif line_count == 8:
            if first_line_len == 5:
                return "五律"
            elif first_line_len == 7:
                return "七律"
        return "古风"


class MetadataGuesser:
    """综合元数据猜测器"""

    def __init__(self):
        self.title = TitleGuesser()
        self.author = AuthorGuesser()
        self.genre = GenreGuesser()

    def guess(self, lines, full_text=None):
        metadata = {
            "title": None,
            "author": None,
            "genre": None,
        }

        for line in lines[:5]:
            if not metadata["title"]:
                metadata["title"] = self.title.guess(line)
            if not metadata["author"]:
                metadata["author"] = self.author.guess(line)
            if not metadata["genre"]:
                metadata["genre"] = self.genre.guess(line)

        if not metadata["genre"]:
            metadata["genre"] = self.genre.guess_from_lines(lines)

        return metadata
