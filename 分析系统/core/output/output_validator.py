# -*- coding: utf-8 -*-
"""Validate output files: readability, format correctness, integrity."""

import json, os, csv, hashlib
import xml.etree.ElementTree as ET
from typing import Any, Optional


class ValidationReport:
    """Collect check results with pass/fail summary."""

    def __init__(self) -> None:
        self._checks: list[dict[str, Any]] = []

    def add_check(self, name: str, passed: bool, detail: str = "") -> None:
        self._checks.append(dict(check=name, passed=passed, detail=detail))

    @property
    def all_passed(self) -> bool:
        return all(c["passed"] for c in self._checks)

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self._checks if c["passed"])

    @property
    def failed_count(self) -> int:
        return sum(1 for c in self._checks if not c["passed"])

    @property
    def total_checks(self) -> int:
        return len(self._checks)

    def failed_checks(self) -> list[dict[str, Any]]:
        return [c for c in self._checks if not c["passed"]]

    def to_dict(self) -> dict[str, Any]:
        return dict(all_passed=self.all_passed, passed=self.passed_count,
                    failed=self.failed_count, total=self.total_checks, checks=self._checks)


class ReadabilityCheck:
    """File existence, non-empty, and encoding validity."""

    @staticmethod
    def exists(filepath: str) -> bool:
        return os.path.isfile(filepath)

    @staticmethod
    def non_empty(filepath: str) -> bool:
        try:
            return os.path.getsize(filepath) > 0
        except OSError:
            return False

    @staticmethod
    def valid_encoding(filepath: str, encoding: str = "utf-8") -> bool:
        try:
            with open(filepath, "r", encoding=encoding) as fh:
                fh.read()
            return True
        except (UnicodeDecodeError, OSError):
            return False


class FormatCheck:
    """Validate JSON, CSV, and XML syntax."""

    @staticmethod
    def is_valid_json(filepath: str) -> bool:
        try:
            json.load(open(filepath, "r", encoding="utf-8"))
            return True
        except (json.JSONDecodeError, OSError):
            return False

    @staticmethod
    def is_valid_csv(filepath: str, delimiter: str = ",") -> bool:
        try:
            next(csv.reader(open(filepath, "r", encoding="utf-8-sig", newline=""), delimiter=delimiter))
            return True
        except (csv.Error, OSError, StopIteration):
            return False

    @staticmethod
    def is_valid_xml(filepath: str) -> bool:
        try:
            ET.parse(filepath)
            return True
        except (ET.ParseError, OSError):
            return False


class IntegrityCheck:
    """Record count matching and checksum verification."""

    @staticmethod
    def record_count_match(filepath: str, expected: int) -> bool:
        try:
            data = json.load(open(filepath, "r", encoding="utf-8"))
            return len(data if isinstance(data, list) else [data]) == expected
        except (json.JSONDecodeError, OSError):
            return False

    @staticmethod
    def checksum_verify(filepath: str, expected_hash: str, algorithm: str = "md5") -> bool:
        try:
            h = hashlib.md5() if algorithm == "md5" else hashlib.sha256()
            with open(filepath, "rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest() == expected_hash.lower()
        except (OSError, ValueError):
            return False


class OutputValidator:
    """Composite validator running readability, format, and integrity checks."""

    def __init__(self) -> None:
        self._r = ReadabilityCheck()
        self._f = FormatCheck()
        self._i = IntegrityCheck()

    def validate(self, filepath: str, format_type: Optional[str] = None,
                 expected_records: Optional[int] = None,
                 expected_hash: Optional[str] = None) -> ValidationReport:
        report = ValidationReport()
        report.add_check("file_exists", self._r.exists(filepath))
        if not self._r.exists(filepath):
            return report
        report.add_check("file_non_empty", self._r.non_empty(filepath))
        report.add_check("valid_encoding", self._r.valid_encoding(filepath))
        if format_type == "json":
            report.add_check("valid_json", self._f.is_valid_json(filepath))
        elif format_type == "csv":
            report.add_check("valid_csv", self._f.is_valid_csv(filepath))
        elif format_type == "xml":
            report.add_check("valid_xml", self._f.is_valid_xml(filepath))
        if expected_records is not None:
            report.add_check("record_count_match", self._i.record_count_match(filepath, expected_records))
        if expected_hash is not None:
            report.add_check("checksum_match", self._i.checksum_verify(filepath, expected_hash))
        return report
