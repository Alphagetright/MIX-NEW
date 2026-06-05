# -*- coding: utf-8 -*-
"""列表工具函数"""

import random


def chunk(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def flatten(items):
    result = []
    for item in items:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def dedup(items, key=None):
    seen = set()
    result = []
    for item in items:
        k = key(item) if key else item
        if k not in seen:
            seen.add(k)
            result.append(item)
    return result


def group_by(items, key_fn):
    result = {}
    for item in items:
        key = key_fn(item)
        if key not in result:
            result[key] = []
        result[key].append(item)
    return result


def sort_by(items, key_fn, reverse=False):
    return sorted(items, key=key_fn, reverse=reverse)


def top_n(items, n, key_fn=None):
    sorted_items = sorted(items, key=key_fn, reverse=True) if key_fn else sorted(items, reverse=True)
    return sorted_items[:n]


def sample(items, n=None, ratio=None):
    if ratio:
        n = max(1, int(len(items) * ratio))
    if n is None:
        n = min(10, len(items))
    n = min(n, len(items))
    return random.sample(items, n)


def partition(items, predicate):
    true_items = []
    false_items = []
    for item in items:
        if predicate(item):
            true_items.append(item)
        else:
            false_items.append(item)
    return true_items, false_items


def sliding_window(items, window_size):
    for i in range(len(items) - window_size + 1):
        yield items[i:i + window_size]


class Paginator:
    """分页器"""

    def __init__(self, items, page_size=25):
        self.items = items
        self.page_size = page_size
        self.total = len(items)
        self.total_pages = max(1, (self.total + page_size - 1) // page_size)

    def get_page(self, page_num):
        page_num = max(1, min(page_num, self.total_pages))
        start = (page_num - 1) * self.page_size
        end = min(start + self.page_size, self.total)
        return {
            "items": self.items[start:end],
            "page": page_num,
            "page_size": self.page_size,
            "total": self.total,
            "total_pages": self.total_pages,
            "has_prev": page_num > 1,
            "has_next": page_num < self.total_pages,
        }

    def iter_pages(self):
        for i in range(1, self.total_pages + 1):
            yield self.get_page(i)
