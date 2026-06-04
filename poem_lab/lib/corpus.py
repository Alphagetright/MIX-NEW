# -*- coding: utf-8 -*-
"""诗歌语料管理 — 本地诗库浏览、检索、统计，不依赖 LLM"""
import json, os, re
from collections import Counter


# 简易倒排索引
class PoemIndex:
    def __init__(self):
        self.poems = []
        self._by_author = {}
        self._by_dynasty = {}
        self._by_form = {}
        self._keyword_index = {}

    def load(self, poems: list):
        """从诗歌列表构建索引"""
        self.poems = poems
        self._by_author = {}
        self._by_dynasty = {}
        self._by_form = {}
        self._keyword_index = {}

        for i, p in enumerate(poems):
            author = p.get("作者", "").strip()
            dynasty = p.get("朝代", "").strip()
            text = p.get("原文", "")
            title = p.get("标题", "")

            if author:
                self._by_author.setdefault(author, []).append(i)
            if dynasty:
                self._by_dynasty.setdefault(dynasty, []).append(i)
            form = self._detect_form(text)
            p["_detected_form"] = form
            if form:
                self._by_form.setdefault(form, []).append(i)

            for word in self._tokenize(title + " " + text):
                self._keyword_index.setdefault(word, set()).add(i)

    def _tokenize(self, text: str) -> list:
        """简易中文分词：按字符 bigram + 单字"""
        chars = re.sub(r'[，。！？、；：""''《》\s,.!?;:\'\"()（）\[\]]', '', text)
        tokens = []
        for i in range(len(chars)):
            tokens.append(chars[i])
            if i < len(chars) - 1:
                tokens.append(chars[i:i+2])
        return list(set(tokens))

    def _detect_form(self, text: str) -> str:
        clean = re.sub(r'[，。！？、；：\s]', '', text)
        length = len(clean)
        if length == 20:
            return "五言绝句"
        elif length == 28:
            return "七言绝句"
        elif length == 40:
            return "五言律诗"
        elif length == 56:
            return "七言律诗"
        elif length > 56:
            return "排律/古风"
        elif 0 < length < 20:
            return "短歌/古体"
        else:
            return "杂言/其他"

    def get_by_author(self, author: str) -> list:
        return [self.poems[i] for i in self._by_author.get(author, [])]

    def get_by_dynasty(self, dynasty: str) -> list:
        return [self.poems[i] for i in self._by_dynasty.get(dynasty, [])]

    def get_by_form(self, form: str) -> list:
        return [self.poems[i] for i in self._by_form.get(form, [])]

    def search(self, keyword: str) -> list:
        indices = set()
        for word in self._tokenize(keyword):
            if word in self._keyword_index:
                indices.update(self._keyword_index[word])
        return [self.poems[i] for i in sorted(indices)]

    def random_sample(self, n: int = 5) -> list:
        import random
        if n >= len(self.poems):
            return self.poems[:]
        return random.sample(self.poems, n)

    @property
    def total(self) -> int:
        return len(self.poems)

    def author_stats(self) -> list:
        stats = []
        for author, indices in self._by_author.items():
            stats.append({"作者": author, "作品数": len(indices)})
        return sorted(stats, key=lambda x: x["作品数"], reverse=True)

    def dynasty_stats(self) -> list:
        stats = []
        for dynasty, indices in self._by_dynasty.items():
            stats.append({"朝代": dynasty, "作品数": len(indices)})
        return sorted(stats, key=lambda x: x["作品数"], reverse=True)

    def form_stats(self) -> list:
        stats = []
        for form, indices in self._by_form.items():
            stats.append({"诗体": form, "作品数": len(indices)})
        return sorted(stats, key=lambda x: x["作品数"], reverse=True)

    def summary(self) -> dict:
        return {
            "总诗歌数": self.total,
            "作者数": len(self._by_author),
            "朝代分布": {d: len(ix) for d, ix in self._by_dynasty.items()},
            "诗体分布": {f: len(ix) for f, ix in self._by_form.items()},
            "词汇量": len(self._keyword_index)
        }

    def top_authors(self, n: int = 10) -> list:
        return self.author_stats()[:n]

    def coauthor_graph(self) -> list:
        """Simple co-occurrence: authors who appear in same dynasty or form."""
        edges = []
        authors = list(self._by_author.keys())
        for i in range(len(authors)):
            for j in range(i + 1, len(authors)):
                a, b = authors[i], authors[j]
                # Check shared dynasty
                dyn_a = set()
                dyn_b = set()
                for idx in self._by_author[a]:
                    p = self.poems[idx]
                    if p.get("朝代"):
                        dyn_a.add(p["朝代"])
                for idx in self._by_author[b]:
                    p = self.poems[idx]
                    if p.get("朝代"):
                        dyn_b.add(p["朝代"])
                shared = dyn_a & dyn_b
                if shared:
                    edges.append({"author_a": a, "author_b": b, "shared_dynasties": list(shared)})
        return edges

    def get_poem_count_by_author(self, author: str) -> int:
        return len(self._by_author.get(author, []))

    def get_poem_count_by_dynasty(self, dynasty: str) -> int:
        return len(self._by_dynasty.get(dynasty, []))

    def search_by_title(self, title_keyword: str) -> list:
        results = []
        for p in self.poems:
            if title_keyword in p.get("标题", ""):
                results.append(p)
        return results

    def get_poems_by_author_and_form(self, author: str, form: str) -> list:
        """按作者+诗体组合筛选"""
        results = []
        for idx in self._by_author.get(author, []):
            p = self.poems[idx]
            if p.get("_detected_form", "") == form:
                results.append(p)
        return results

    def author_dynasty_matrix(self) -> list:
        """作者-朝代矩阵统计"""
        matrix = {}
        for author, indices in self._by_author.items():
            dynasties = Counter()
            for idx in indices:
                d = self.poems[idx].get("朝代", "未知") or "未知"
                dynasties[d] += 1
            matrix[author] = dict(dynasties)
        return [{"作者": a, "朝代分布": d} for a, d in matrix.items()]

    def search_by_text(self, keyword: str) -> list:
        results = []
        for p in self.poems:
            if keyword in p.get("原文", ""):
                results.append(p)
        return results

    def compare_dynasties(self, d1: str, d2: str) -> dict:
        poems1 = self.get_by_dynasty(d1)
        poems2 = self.get_by_dynasty(d2)
        authors1 = set(p.get("作者","") for p in poems1)
        authors2 = set(p.get("作者","") for p in poems2)
        forms1 = Counter(p.get("_detected_form","") for p in poems1)
        forms2 = Counter(p.get("_detected_form","") for p in poems2)
        return {
            "朝代A": {"名": d1, "作品数": len(poems1), "作者数": len(authors1), "诗体分布": dict(forms1)},
            "朝代B": {"名": d2, "作品数": len(poems2), "作者数": len(authors2), "诗体分布": dict(forms2)},
            "共用作者": list(authors1 & authors2)
        }


# 全局索引实例
_index = PoemIndex()


def build_index(poems: list) -> PoemIndex:
    global _index
    _index = PoemIndex()
    _index.load(poems)
    return _index


def get_index() -> PoemIndex:
    return _index
