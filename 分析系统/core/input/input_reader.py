# -*- coding: utf-8 -*-
"""多格式输入读取 —— TXT/JSON/CSV/MD/XML 自动检测"""

import os
import json


class FormatDetector:
    """格式自动检测"""

    def __init__(self):
        self._detectors = {
            ".json": self._detect_json,
            ".csv": self._detect_csv,
            ".md": self._detect_md,
            ".txt": self._detect_txt,
            ".xml": self._detect_xml,
        }

    def detect(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        return self._detectors.get(ext, self._detect_txt)

    def _detect_json(self, content):
        return "json"

    def _detect_csv(self, content):
        return "csv"

    def _detect_md(self, content):
        return "md"

    def _detect_txt(self, content):
        return "txt"

    def _detect_xml(self, content):
        return "xml"


class TextFileReader:
    """文本文件读取器"""

    def __init__(self, encoding="utf-8", fallback_encodings=None):
        self.encoding = encoding
        self.fallback_encodings = fallback_encodings or ["gbk", "gb2312", "utf-16", "latin-1"]

    def read(self, filepath):
        try:
            with open(filepath, "r", encoding=self.encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            for enc in self.fallback_encodings:
                try:
                    with open(filepath, "r", encoding=enc) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            with open(filepath, "r", encoding=self.encoding, errors="replace") as f:
                return f.read()

    def read_lines(self, filepath):
        text = self.read(filepath)
        return text.splitlines()


class JSONFileReader:
    """JSON文件读取器"""

    def __init__(self):
        self._text_reader = TextFileReader()

    def read(self, filepath):
        content = self._text_reader.read(filepath)
        return json.loads(content)

    def read_poems(self, filepath, poem_key=None):
        data = self.read(filepath)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if "诗歌集" in data:
                return data["诗歌集"]
            if "poems" in data:
                return data["poems"]
            if poem_key and poem_key in data:
                return data[poem_key]
            return self._extract_all_values(data)
        return []

    def _extract_all_values(self, data):
        values = []
        for key, value in data.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value
            elif isinstance(value, dict):
                result = self._extract_all_values(value)
                if result:
                    return result
        return values


class CSVFileReader:
    """CSV文件读取器"""

    def __init__(self):
        import csv
        self.csv = csv

    def read(self, filepath, encoding="utf-8"):
        with open(filepath, "r", encoding=encoding) as f:
            reader = self.csv.DictReader(f)
            return list(reader)

    def read_simple(self, filepath, encoding="utf-8"):
        with open(filepath, "r", encoding=encoding) as f:
            reader = self.csv.reader(f)
            return list(reader)


class InputReader:
    """统一输入读取器 —— 自动检测格式并读取"""

    def __init__(self):
        self._readers = {
            "json": JSONFileReader(),
            "txt": TextFileReader(),
            "csv": CSVFileReader(),
            "md": TextFileReader(),
            "xml": TextFileReader(),
        }
        self._detector = FormatDetector()

    def read(self, filepath):
        _, ext = os.path.splitext(filepath)
        ext = ext.lstrip(".").lower()
        reader = self._readers.get(ext)
        if not reader:
            return self._readers["txt"].read(filepath)
        return reader.read(filepath)

    def read_text(self, filepath):
        return TextFileReader().read(filepath)

    def read_structured(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".json":
            return {"format": "json", "data": JSONFileReader().read(filepath)}
        elif ext == ".csv":
            return {"format": "csv", "data": CSVFileReader().read(filepath)}
        else:
            return {"format": "text", "data": TextFileReader().read(filepath)}
