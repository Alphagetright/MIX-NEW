# -*- coding: utf-8 -*-
"""JSON serializer with encoding control, streaming, and sharding."""

import json, os, math
from typing import Any, Callable, Optional


class JsonEncodeError(Exception):
    pass


class SerializeConfig:
    def __init__(self, indent: int = 2, ensure_ascii: bool = False,
                 sort_keys: bool = False,
                 default_handler: Optional[Callable[[Any], Any]] = None) -> None:
        self.indent, self.ensure_ascii = indent, ensure_ascii
        self.sort_keys, self.default_handler = sort_keys, default_handler or (
            lambda o: (_ for _ in ()).throw(TypeError(f"Type {type(o).__name__} not serialisable")))

    def to_json_kwargs(self) -> dict:
        return dict(indent=self.indent, ensure_ascii=self.ensure_ascii,
                    sort_keys=self.sort_keys, default=self.default_handler)


class StreamWriter:
    """Incremental JSON array writer that flushes chunks to disk."""

    def __init__(self, filepath: str, config: Optional[SerializeConfig] = None) -> None:
        self.filepath, self.config = filepath, config or SerializeConfig()
        self._buffer: list[str] = []

    def write_chunk(self, chunk: Any) -> None:
        try:
            self._buffer.append(json.dumps(chunk, **self.config.to_json_kwargs()))
        except (TypeError, ValueError) as exc:
            raise JsonEncodeError(str(exc)) from exc

    def flush(self) -> None:
        d = os.path.dirname(self.filepath)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as fh:
            fh.write("[\n")
            for idx, chunk in enumerate(self._buffer):
                fh.write((",\n" if idx else "") + chunk)
            fh.write("\n]\n")
        self._buffer.clear()

    def __enter__(self) -> "StreamWriter":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        if self._buffer:
            self.flush()


class ShardManager:
    def __init__(self, base_path: str, records_per_shard: int = 5000,
                 config: Optional[SerializeConfig] = None) -> None:
        self.base_path, self.records_per_shard = base_path, records_per_shard
        self.config = config or SerializeConfig()

    def write_shards(self, records: list[Any]) -> list[str]:
        if not records:
            return []
        n = max(1, math.ceil(len(records) / self.records_per_shard))
        paths: list[str] = []
        stem, ext = os.path.splitext(self.base_path)
        for i in range(n):
            start, end = i * self.records_per_shard, (i + 1) * self.records_per_shard
            sp = f"{stem}_shard_{i + 1:04d}{ext}"
            paths.append(sp)
            d = os.path.dirname(sp)
            if d and not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
            try:
                with open(sp, "w", encoding="utf-8") as fh:
                    json.dump(records[start:end], fh, **self.config.to_json_kwargs())
            except (TypeError, ValueError, OSError) as exc:
                raise JsonEncodeError(f"Shard {i + 1} failed: {exc}") from exc
        return paths


class JsonSerializer:
    """Single entry point for serialize, deserialize, stream, and shard."""

    def __init__(self, config: Optional[SerializeConfig] = None) -> None:
        self.config = config or SerializeConfig()

    def serialize(self, data: Any, filepath: str) -> None:
        d = os.path.dirname(filepath)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
        try:
            with open(filepath, "w", encoding="utf-8") as fh:
                json.dump(data, fh, **self.config.to_json_kwargs())
        except (TypeError, ValueError, OSError) as exc:
            raise JsonEncodeError(str(exc)) from exc

    def deserialize(self, filepath: str) -> Any:
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            raise JsonEncodeError(str(exc)) from exc

    def stream(self, filepath: str) -> StreamWriter:
        return StreamWriter(filepath, self.config)

    def shard(self, base_path: str, records: list[Any]) -> list[str]:
        return ShardManager(base_path, config=self.config).write_shards(records)
