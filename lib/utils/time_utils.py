# -*- coding: utf-8 -*-
"""时间工具函数"""

import time
import datetime


def now():
    return time.time()


def now_str(fmt="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.now().strftime(fmt)


def format_timestamp(ts, fmt="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.fromtimestamp(ts).strftime(fmt)


def parse_time(text, fmt="%Y-%m-%d %H:%M:%S"):
    try:
        dt = datetime.datetime.strptime(text, fmt)
        return dt.timestamp()
    except ValueError:
        return None


def time_diff(start, end=None):
    end = end or time.time()
    return end - start


def format_duration(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    elif seconds < 86400:
        return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
    else:
        return f"{seconds // 86400}d {(seconds % 86400) // 3600}h"


class Timer:
    """计时器"""

    def __init__(self):
        self.start_time = None
        self.elapsed = 0

    def start(self):
        self.start_time = time.time()
        return self

    def stop(self):
        if self.start_time:
            self.elapsed = time.time() - self.start_time
            self.start_time = None
        return self.elapsed

    def reset(self):
        self.start_time = None
        self.elapsed = 0

    def reading(self):
        if self.start_time:
            return time.time() - self.start_time
        return self.elapsed

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


class RateLimiter:
    """速率限制器"""

    def __init__(self, max_calls=10, window=1.0):
        self.max_calls = max_calls
        self.window = window
        self._calls = []

    def acquire(self):
        now = time.time()
        cutoff = now - self.window
        self._calls = [t for t in self._calls if t > cutoff]
        if len(self._calls) >= self.max_calls:
            sleep_time = self._calls[0] + self.window - now
            if sleep_time > 0:
                time.sleep(sleep_time)
        self._calls.append(time.time())

    def __call__(self, fn):
        def wrapper(*args, **kwargs):
            self.acquire()
            return fn(*args, **kwargs)
        return wrapper


class Throttle:
    """节流器 —— 固定间隔执行"""

    def __init__(self, interval=1.0):
        self.interval = interval
        self._last_call = 0

    def wait(self):
        now = time.time()
        since_last = now - self._last_call
        if since_last < self.interval:
            time.sleep(self.interval - since_last)
        self._last_call = time.time()
