# -*- coding: utf-8 -*-
"""配置监视 —— 配置文件变化检测与热加载"""

import os
import time
import threading


class ConfigWatcher:
    """配置监视器 —— 文件变化自动检测"""

    def __init__(self, filepath, interval=5.0):
        self.filepath = filepath
        self.interval = interval
        self._mtime = None
        self._running = False
        self._thread = None
        self._callbacks = []
        self._lock = threading.Lock()

    def start(self):
        if self._running:
            return
        self._mtime = self._get_mtime()
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def on_change(self, callback):
        self._callbacks.append(callback)

    def _watch_loop(self):
        while self._running:
            try:
                current = self._get_mtime()
                if current and self._mtime and current != self._mtime:
                    self._mtime = current
                    self._notify()
            except Exception:
                pass
            time.sleep(self.interval)

    def _get_mtime(self):
        try:
            if os.path.exists(self.filepath):
                return os.path.getmtime(self.filepath)
        except Exception:
            pass
        return None

    def _notify(self):
        for callback in self._callbacks:
            try:
                callback(self.filepath)
            except Exception:
                pass

    @property
    def is_running(self):
        return self._running


class ConfigReloader:
    """配置热加载器"""

    def __init__(self, loader, filepath):
        self.loader = loader
        self.filepath = filepath
        self._watcher = ConfigWatcher(filepath)
        self._current_config = None
        self._reload_callbacks = []

    def load(self):
        data = self.loader.load_file(self.filepath)
        self._current_config = data
        return data

    def start_watching(self):
        self._watcher.on_change(self._on_file_changed)
        self._watcher.start()

    def stop_watching(self):
        self._watcher.stop()

    def on_reload(self, callback):
        self._reload_callbacks.append(callback)

    def _on_file_changed(self, filepath):
        try:
            data = self.loader.load_file(filepath)
            self._current_config = data
            for cb in self._reload_callbacks:
                cb(data)
        except Exception:
            pass

    @property
    def current(self):
        return self._current_config
