# -*- coding: utf-8 -*-
"""CSV serializer with BOM, quoting, multi-sheet emulation, readback."""

import csv, os, io
from typing import Any, Optional


class CsvConfig:
    def __init__(self, delimiter: str = ",", quote_char: str = '"', bom: bool = True,
                 header_writing: bool = True, quoting: int = csv.QUOTE_MINIMAL) -> None:
        self.delimiter, self.quote_char = delimiter, quote_char
        self.bom, self.header_writing, self.quoting = bom, header_writing, quoting

    def _dialect(self) -> type[csv.Dialect]:
        class _D(csv.Dialect):
            delimiter = self.delimiter
            quotechar = self.quote_char
            quoting = self.quoting
            doublequote = True
            skipinitialspace = False
            lineterminator = "\r\n"
            escapechar = None
        return _D


class CsvFormatter:
    def __init__(self, config: Optional[CsvConfig] = None) -> None:
        self.config = config or CsvConfig()

    def format_value(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return str(value).upper()
        if isinstance(value, (int, float)):
            return str(value)
        return str(value)

    def format_row(self, row: dict[str, Any], headers: list[str]) -> list[str]:
        return [self.format_value(row.get(h, "")) for h in headers]


class SheetWriter:
    def __init__(self, directory: str, config: Optional[CsvConfig] = None) -> None:
        self.directory, self.config = directory, config or CsvConfig()

    def write_sheet(self, name: str, headers: list[str], rows: list[dict]) -> str:
        if not os.path.exists(self.directory):
            os.makedirs(self.directory, exist_ok=True)
        fp = os.path.join(self.directory, f"{name}.csv")
        dialect = self.config._dialect()
        with open(fp, "wb") as fh:
            if self.config.bom:
                fh.write(b"\xef\xbb\xbf")
            tw = io.TextIOWrapper(fh, encoding="utf-8", newline="")
            w = csv.writer(tw, dialect=dialect)
            if self.config.header_writing:
                w.writerow(headers)
            fm = CsvFormatter(self.config)
            for row in rows:
                w.writerow(fm.format_row(row, headers))
            tw.flush()
        return fp


class CsvReadback:
    def __init__(self, config: Optional[CsvConfig] = None) -> None:
        self.config = config or CsvConfig()

    def read(self, fp: str) -> tuple[list[str], list[list[str]]]:
        dialect = self.config._dialect()
        with open(fp, "r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.reader(fh, dialect=dialect)
            headers = next(reader) if self.config.header_writing else []
            return headers, list(reader)

    def verify(self, fp: str, expected_row_count: int) -> bool:
        try:
            _, rows = self.read(fp)
            return len(rows) == expected_row_count
        except Exception:
            return False


class CsvSerializer:
    """High-level CSV serialiser with multi-sheet support."""

    def __init__(self, config: Optional[CsvConfig] = None) -> None:
        self.config = config or CsvConfig()

    def write(self, fp: str, headers: list[str], rows: list[dict]) -> None:
        d = os.path.dirname(fp)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
        dialect = self.config._dialect()
        with open(fp, "wb") as fh:
            if self.config.bom:
                fh.write(b"\xef\xbb\xbf")
            tw = io.TextIOWrapper(fh, encoding="utf-8", newline="")
            w = csv.writer(tw, dialect=dialect)
            if self.config.header_writing:
                w.writerow(headers)
            fm = CsvFormatter(self.config)
            for row in rows:
                w.writerow(fm.format_row(row, headers))
            tw.flush()

    def multi_sheet(self, directory: str,
                    sheets: dict[str, tuple[list[str], list[dict]]]) -> list[str]:
        sw = SheetWriter(directory, self.config)
        return [sw.write_sheet(n, h, r) for n, (h, r) in sheets.items()]

    def readback(self, fp: str) -> CsvReadback:
        return CsvReadback(self.config)
