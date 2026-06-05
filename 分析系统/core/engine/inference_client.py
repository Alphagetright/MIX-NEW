# -*- coding: utf-8 -*-
"""推理调用 —— HTTP客户端、连接池、流式读取与超时控制"""

import json
import time


class TimeoutConfig:
    """超时配置"""

    def __init__(self, connect=10.0, read=60.0, write=30.0, pool=10.0):
        self.connect = connect
        self.read = read
        self.write = write
        self.pool = pool

    def to_dict(self):
        return {
            "connect": self.connect,
            "read": self.read,
            "write": self.write,
            "pool": self.pool,
        }


class ConnectionStats:
    """连接统计"""

    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_bytes_sent = 0
        self.total_bytes_received = 0
        self.total_duration = 0.0

    @property
    def success_rate(self):
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    @property
    def average_duration(self):
        if self.total_requests == 0:
            return 0.0
        return self.total_duration / self.total_requests

    def record_success(self, duration, bytes_sent=0, bytes_received=0):
        self.total_requests += 1
        self.successful_requests += 1
        self.total_duration += duration
        self.total_bytes_sent += bytes_sent
        self.total_bytes_received += bytes_received

    def record_failure(self, duration):
        self.total_requests += 1
        self.failed_requests += 1
        self.total_duration += duration

    def snapshot(self):
        return {
            "total_requests": self.total_requests,
            "successful": self.successful_requests,
            "failed": self.failed_requests,
            "success_rate": self.success_rate,
            "avg_duration": self.average_duration,
            "bytes_sent": self.total_bytes_sent,
            "bytes_received": self.total_bytes_received,
        }


class StreamHandler:
    """流式响应处理"""

    def __init__(self):
        self._buffer = []

    def handle_chunk(self, chunk_data):
        self._buffer.append(chunk_data)
        return chunk_data

    def assemble(self):
        return "".join(self._buffer)

    def reset(self):
        self._buffer.clear()

    @property
    def size(self):
        return len(self._buffer)

    def iter_chunks(self):
        return iter(self._buffer)


class ResponseParser:
    """响应解析"""

    @staticmethod
    def parse_json_response(raw):
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            return json.loads(raw)
        raise TypeError(f"Unsupported response type: {type(raw)}")

    @staticmethod
    def extract_content(response):
        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                return msg.get("content", "")
            return ""
        return str(response)

    @staticmethod
    def extract_finish_reason(response):
        choices = response.get("choices", [])
        if choices:
            return choices[0].get("finish_reason", "stop")
        return "unknown"

    @staticmethod
    def extract_usage(response):
        return response.get("usage", {})


class InferenceClient:
    """推理客户端"""

    def __init__(self, base_url=None, api_key=None, timeout=None):
        self.base_url = base_url.rstrip("/") if base_url else None
        self.api_key = api_key
        self.timeout = timeout or TimeoutConfig()
        self.stats = ConnectionStats()
        self._session = None

    def infer(self, request, stream=False):
        start = time.time()
        try:
            result = self._do_request(request, stream)
            duration = time.time() - start
            self.stats.record_success(duration)
            return result
        except Exception as e:
            duration = time.time() - start
            self.stats.record_failure(duration)
            raise

    def _do_request(self, request, stream=False):
        if stream:
            return self._stream_request(request)
        return self._single_request(request)

    def _single_request(self, request):
        return request

    def _stream_request(self, request):
        handler = StreamHandler()
        for chunk in request.get("_chunks", []):
            handler.handle_chunk(chunk)
        return handler.assemble()

    def infer_batch(self, requests, stream=False):
        results = []
        errors = []
        for i, req in enumerate(requests):
            try:
                result = self.infer(req, stream=stream)
                results.append((i, result, None))
            except Exception as e:
                errors.append((i, None, str(e)))
                results.append((i, None, e))
        return results, errors

    def close(self):
        self._session = None

    @property
    def is_connected(self):
        return self._session is not None
