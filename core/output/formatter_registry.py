# -*- coding: utf-8 -*-
"""Registry for discovering and auto-selecting output formatters."""

import os
from typing import Any, Optional, Type


class FormatEntry:
    """Metadata: name, extension, formatter class, and description."""

    def __init__(self, name: str, extension: str, formatter_class: Type[Any],
                 description: str = "") -> None:
        self.name = name
        self.extension = extension.lstrip(".")
        self.formatter_class = formatter_class
        self.description = description

    @property
    def extension_with_dot(self) -> str:
        return f".{self.extension}"

    def __repr__(self) -> str:
        return f"FormatEntry('{self.name}', '.{self.extension}')"


class FormatDetector:
    """Detect format from filename, extension, or content."""

    def __init__(self, registry: "FormatterRegistry") -> None:
        self._entries = registry._entries

    def from_filename(self, filepath: str) -> Optional[str]:
        ext = os.path.splitext(filepath)[1].lstrip(".").lower()
        for e in self._entries.values():
            if e.extension.lower() == ext:
                return e.name
        return None

    def from_extension(self, extension: str) -> Optional[str]:
        ext = extension.lstrip(".").lower()
        for e in self._entries.values():
            if e.extension.lower() == ext:
                return e.name
        return None


class RegistryStats:
    """Summary statistics for a registry."""

    def __init__(self, entries: list[FormatEntry]) -> None:
        self._entries = entries

    @property
    def count(self) -> int:
        return len(self._entries)

    @property
    def extensions(self) -> list[str]:
        return sorted({e.extension.lower() for e in self._entries})

    @property
    def names(self) -> list[str]:
        return sorted(e.name for e in self._entries)

    def __repr__(self) -> str:
        return f"RegistryStats(count={self.count})"


class FormatterRegistry:
    """Central registry — register, retrieve, instantiate, auto-select."""

    def __init__(self) -> None:
        self._entries: dict[str, FormatEntry] = {}

    def register(self, name: str, extension: str, formatter_class: Type[Any],
                 description: str = "") -> None:
        if name in self._entries:
            raise KeyError(f"Formatter '{name}' already registered")
        self._entries[name] = FormatEntry(name, extension, formatter_class, description)

    def unregister(self, name: str) -> None:
        if name not in self._entries:
            raise KeyError(f"Formatter '{name}' not registered")
        del self._entries[name]

    def get(self, name: str) -> FormatEntry:
        if name not in self._entries:
            raise KeyError(f"Formatter '{name}' not registered")
        return self._entries[name]

    def instantiate(self, name: str, **kwargs: Any) -> Any:
        return self.get(name).formatter_class(**kwargs)

    def list_formats(self) -> list[FormatEntry]:
        return list(self._entries.values())

    def auto_select(self, filepath: str) -> Optional[str]:
        return FormatDetector(self).from_filename(filepath)

    @property
    def stats(self) -> RegistryStats:
        return RegistryStats(self.list_formats())

    def __contains__(self, name: str) -> bool:
        return name in self._entries

    def __len__(self) -> int:
        return len(self._entries)
