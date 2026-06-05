# -*- coding: utf-8 -*-
"""审计日志 —— 操作记录与数据变更追踪"""

import json
import time
import uuid
import threading


class AuditEntry:
    """审计条目"""

    def __init__(self, action, target, user=None, detail=None):
        self.id = str(uuid.uuid4())[:12]
        self.timestamp = time.time()
        self.action = action
        self.target = target
        self.user = user
        self.detail = detail or {}

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "action": self.action,
            "target": self.target,
            "user": self.user,
            "detail": self.detail,
        }

    def format_time(self, fmt="%Y-%m-%d %H:%M:%S"):
        import datetime
        return datetime.datetime.fromtimestamp(self.timestamp).strftime(fmt)


class AuditLogger:
    """审计日志器"""

    def __init__(self, backend=None):
        self._backend = backend or MemoryAuditBackend()
        self._lock = threading.Lock()

    def record(self, action, target, user=None, detail=None):
        entry = AuditEntry(action, target, user, detail)
        with self._lock:
            self._backend.store(entry)
        return entry

    def query(self, action=None, target=None, user=None, limit=100):
        with self._lock:
            return self._backend.query(action, target, user, limit)

    def summary(self):
        with self._lock:
            return self._backend.summary()


class MemoryAuditBackend:
    """内存审计存储后端"""

    def __init__(self, max_entries=10000):
        self._entries = []
        self.max_entries = max_entries

    def store(self, entry):
        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries:]

    def query(self, action=None, target=None, user=None, limit=100):
        results = self._entries
        if action:
            results = [e for e in results if e.action == action]
        if target:
            results = [e for e in results if e.target == target]
        if user:
            results = [e for e in results if e.user == user]
        return results[-limit:]

    def summary(self):
        from collections import Counter
        actions = Counter(e.action for e in self._entries)
        targets = Counter(e.target for e in self._entries)
        users = Counter(e.user for e in self._entries if e.user)
        return {
            "total": len(self._entries),
            "actions": dict(actions.most_common(20)),
            "top_targets": dict(targets.most_common(10)),
            "users": len(users),
        }


class FileAuditBackend:
    """文件审计存储后端"""

    def __init__(self, filepath):
        self.filepath = filepath
        self._entries = []
        self._loaded = False

    def _ensure_loaded(self):
        if not self._loaded:
            try:
                import os
                if os.path.exists(self.filepath):
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                data = json.loads(line)
                                entry = AuditEntry(
                                    data["action"], data["target"],
                                    data.get("user"), data.get("detail", {}),
                                )
                                entry.id = data["id"]
                                entry.timestamp = data["timestamp"]
                                self._entries.append(entry)
            except Exception:
                pass
            self._loaded = True

    def store(self, entry):
        self._ensure_loaded()
        self._entries.append(entry)
        try:
            import os
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass

    def query(self, action=None, target=None, user=None, limit=100):
        self._ensure_loaded()
        results = self._entries
        if action:
            results = [e for e in results if e.action == action]
        if target:
            results = [e for e in results if e.target == target]
        if user:
            results = [e for e in results if e.user == user]
        return results[-limit:]

    def summary(self):
        self._ensure_loaded()
        from collections import Counter
        return {
            "total": len(self._entries),
            "actions": dict(Counter(e.action for e in self._entries).most_common(20)),
        }
