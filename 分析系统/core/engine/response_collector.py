# -*- coding: utf-8 -*-
"""响应收集 —— 流式块合并、完整响应组装、原始结果缓存"""

import time
import json


class ResponseChunk:
    """响应块"""

    def __init__(self, data, index=0, timestamp=None):
        self.data = data
        self.index = index
        self.timestamp = timestamp or time.time()

    @property
    def size(self):
        return len(str(self.data))

    def to_dict(self):
        return {
            "index": self.index,
            "data": self.data,
            "timestamp": self.timestamp,
            "size": self.size,
        }


class ResponseBuffer:
    """响应缓冲"""

    def __init__(self):
        self._chunks = []
        self._completed = False

    def add(self, chunk):
        if isinstance(chunk, ResponseChunk):
            self._chunks.append(chunk)
        else:
            self._chunks.append(ResponseChunk(chunk, index=len(self._chunks)))

    def add_all(self, chunks):
        for chunk in chunks:
            self.add(chunk)

    @property
    def chunks(self):
        return list(self._chunks)

    @property
    def size(self):
        return sum(c.size for c in self._chunks)

    @property
    def count(self):
        return len(self._chunks)

    def mark_completed(self):
        self._completed = True

    @property
    def is_completed(self):
        return self._completed

    def clear(self):
        self._chunks.clear()
        self._completed = False


class ResponseAssembler:
    """响应组装器"""

    def __init__(self):
        self._buffer = ResponseBuffer()

    def add_chunk(self, chunk_data):
        self._buffer.add(chunk_data)

    def assemble_text(self):
        parts = []
        for chunk in self._buffer.chunks:
            data = chunk.data
            if isinstance(data, dict):
                content = data.get("content") or data.get("text", "")
                parts.append(str(content))
            elif isinstance(data, str):
                parts.append(data)
            else:
                parts.append(str(data))
        return "".join(parts)

    def assemble_json(self):
        text = self.assemble_text()
        if not text.strip():
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def assemble_structured(self, parser_fn):
        text = self.assemble_text()
        if parser_fn:
            return parser_fn(text)
        return text

    def reset(self):
        self._buffer.clear()


class ResponseMetadata:
    """响应元数据"""

    def __init__(self):
        self.model = None
        self.finish_reason = None
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.start_time = None
        self.end_time = None
        self.request_id = None

    @property
    def duration(self):
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0

    def to_dict(self):
        return {
            "model": self.model,
            "finish_reason": self.finish_reason,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "duration": self.duration,
            "request_id": self.request_id,
        }


class RawResponseCache:
    """原始响应缓存"""

    def __init__(self, max_entries=100):
        self._cache = {}
        self._max_entries = max_entries
        self._access_order = []

    def put(self, key, response):
        if key in self._cache:
            self._access_order.remove(key)
        elif len(self._cache) >= self._max_entries:
            oldest = self._access_order.pop(0)
            self._cache.pop(oldest)
        self._cache[key] = {
            "response": response,
            "timestamp": time.time(),
        }
        self._access_order.append(key)

    def get(self, key):
        entry = self._cache.get(key)
        if entry:
            return entry["response"]
        return None

    def has(self, key):
        return key in self._cache

    def remove(self, key):
        if key in self._cache:
            self._cache.pop(key)
            self._access_order.remove(key)

    def clear(self):
        self._cache.clear()
        self._access_order.clear()

    @property
    def size(self):
        return len(self._cache)

    def stats(self):
        return {
            "entries": len(self._cache),
            "max_entries": self._max_entries,
            "keys": list(self._cache.keys()),
        }


class ResponseCollector:
    """响应收集器"""

    def __init__(self):
        self.assembler = ResponseAssembler()
        self.metadata = ResponseMetadata()
        self.cache = RawResponseCache()

    def start(self):
        self.metadata.start_time = time.time()
        self.assembler.reset()

    def collect(self, chunk_data):
        self.assembler.add_chunk(chunk_data)

    def finish(self, metadata_updates=None):
        self.metadata.end_time = time.time()
        if metadata_updates:
            for key, value in metadata_updates.items():
                if hasattr(self.metadata, key):
                    setattr(self.metadata, key, value)
        return self.get_result()

    def get_result(self):
        return {
            "text": self.assembler.assemble_text(),
            "json": self.assembler.assemble_json(),
            "metadata": self.metadata.to_dict(),
        }

    def get_text(self):
        return self.assembler.assemble_text()

    def get_json(self):
        return self.assembler.assemble_json()

    def cache_result(self, cache_key):
        result = self.get_result()
        self.cache.put(cache_key, result)
        return result

    def load_cached(self, cache_key):
        return self.cache.get(cache_key)
