# -*- coding: utf-8 -*-
"""序列化工具函数"""

import json
import copy
import hashlib
import base64


def deep_clone(obj):
    return copy.deepcopy(obj)


def to_json(obj, ensure_ascii=False, indent=2):
    return json.dumps(obj, ensure_ascii=ensure_ascii, indent=indent, default=str)


def from_json(json_str):
    return json.loads(json_str)


def to_base64(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.b64encode(data).decode("ascii")


def from_base64(encoded):
    return base64.b64decode(encoded)


def to_hex(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return data.hex()


def from_hex(hex_str):
    return bytes.fromhex(hex_str)


def compute_hash(data, algorithm="sha256"):
    h = hashlib.new(algorithm)
    if isinstance(data, str):
        data = data.encode("utf-8")
    h.update(data)
    return h.hexdigest()


def compute_file_hash(filepath, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class Serializer:
    """通用序列化器"""

    def __init__(self, format="json"):
        self.format = format

    def serialize(self, obj):
        if self.format == "json":
            return to_json(obj)
        elif self.format == "base64":
            return to_base64(to_json(obj))
        raise ValueError(f"Unsupported format: {self.format}")

    def deserialize(self, data):
        if self.format == "json":
            return from_json(data)
        elif self.format == "base64":
            return from_json(from_base64(data))
        raise ValueError(f"Unsupported format: {self.format}")


class Checksum:
    """校验和计算"""

    @staticmethod
    def md5(data):
        return compute_hash(data, "md5")

    @staticmethod
    def sha256(data):
        return compute_hash(data, "sha256")

    @staticmethod
    def verify(data, checksum, algorithm="sha256"):
        return compute_hash(data, algorithm) == checksum
