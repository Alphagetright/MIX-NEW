# -*- coding: utf-8 -*-
"""编码自动检测与转换"""

import os


BOM_SIGNATURES = {
    "utf-8-sig": b"\xef\xbb\xbf",
    "utf-16-le": b"\xff\xfe",
    "utf-16-be": b"\xfe\xff",
    "utf-32-le": b"\xff\xfe\x00\x00",
    "utf-32-be": b"\x00\x00\xfe\xff",
}


class BOMDetector:
    """BOM标记检测"""

    def detect(self, filepath):
        with open(filepath, "rb") as f:
            header = f.read(4)
        for encoding, signature in BOM_SIGNATURES.items():
            if header.startswith(signature):
                return encoding
        return None

    def has_bom(self, filepath):
        return self.detect(filepath) is not None

    def strip_bom(self, data):
        for encoding, signature in BOM_SIGNATURES.items():
            if data.startswith(signature):
                return data[len(signature):]
        return data


class EncodingDetector:
    """编码自动检测器"""

    def __init__(self):
        self._bom_detector = BOMDetector()

    def detect(self, filepath):
        bom = self._bom_detector.detect(filepath)
        if bom:
            return bom

        with open(filepath, "rb") as f:
            sample = f.read(4096)

        for enc in ["utf-8", "gbk", "gb2312", "utf-16", "latin-1"]:
            try:
                sample.decode(enc)
                return enc
            except (UnicodeDecodeError, LookupError):
                continue

        return "utf-8"

    def detect_with_confidence(self, filepath):
        with open(filepath, "rb") as f:
            sample = f.read(4096)

        bom = self._bom_detector.detect(filepath)
        if bom:
            return {"encoding": bom, "confidence": 1.0, "method": "bom"}

        results = []
        for enc in ["utf-8", "gbk", "gb2312", "big5", "utf-16", "shift_jis", "euc-kr", "latin-1"]:
            try:
                sample.decode(enc)
                confidence = 0.9 if enc == "utf-8" else 0.6
                results.append({"encoding": enc, "confidence": confidence})
            except UnicodeDecodeError:
                pass

        if results:
            results.sort(key=lambda x: -x["confidence"])
            results[0]["method"] = "heuristic"
            return results[0]

        return {"encoding": "latin-1", "confidence": 0.1, "method": "fallback"}


class EncodingConverter:
    """编码转换器"""

    def __init__(self, target_encoding="utf-8"):
        self.target = target_encoding

    def convert_file(self, filepath, source_encoding=None, output_path=None):
        if not source_encoding:
            detector = EncodingDetector()
            source_encoding = detector.detect(filepath)

        output_path = output_path or filepath
        with open(filepath, "r", encoding=source_encoding, errors="replace") as f:
            content = f.read()

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding=self.target) as f:
            f.write(content)

        return {"source": source_encoding, "target": self.target, "path": output_path}

    def convert_data(self, data, source_encoding):
        return data.decode(source_encoding, errors="replace")


class EncodingValidator:
    """编码有效性验证"""

    @staticmethod
    def is_valid_utf8(data):
        try:
            if isinstance(data, bytes):
                data.decode("utf-8")
            return True
        except (UnicodeDecodeError, AttributeError):
            return False

    @staticmethod
    def validate_file(filepath):
        with open(filepath, "rb") as f:
            raw = f.read(4096)
        return {
            "is_valid_utf8": EncodingValidator.is_valid_utf8(raw),
            "has_bom": BOMDetector().has_bom(filepath),
            "file_size": os.path.getsize(filepath),
        }
