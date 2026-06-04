# -*- coding: utf-8 -*-
"""熔断器 —— 防止级联失败的熔断保护机制"""

import time
import threading


class CircuitBreaker:
    """熔断器 —— 状态机：CLOSED / OPEN / HALF_OPEN"""

    STATE_CLOSED = "CLOSED"
    STATE_OPEN = "OPEN"
    STATE_HALF_OPEN = "HALF_OPEN"

    def __init__(self, failure_threshold=5, recovery_timeout=30, half_open_max_calls=1):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = self.STATE_CLOSED
        self._failure_count = 0
        self._last_failure_time = 0
        self._half_open_calls = 0
        self._lock = threading.Lock()
        self._on_state_change = None

    @property
    def state(self):
        return self._state

    def on_state_change(self, callback):
        self._on_state_change = callback

    def call(self, fn, *args, **kwargs):
        if not self._allow_request():
            raise Exception(f"Circuit breaker is OPEN, request blocked")

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _allow_request(self):
        with self._lock:
            if self._state == self.STATE_OPEN:
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._set_state(self.STATE_HALF_OPEN)
                    self._half_open_calls = 0
                    return True
                return False
            if self._state == self.STATE_HALF_OPEN:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            return True

    def _on_success(self):
        with self._lock:
            if self._state == self.STATE_HALF_OPEN:
                self._set_state(self.STATE_CLOSED)
                self._failure_count = 0
            self._failure_count = max(0, self._failure_count - 1)

    def _on_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._state == self.STATE_HALF_OPEN:
                self._set_state(self.STATE_OPEN)
            elif self._failure_count >= self.failure_threshold:
                self._set_state(self.STATE_OPEN)

    def _set_state(self, new_state):
        old_state = self._state
        self._state = new_state
        if self._on_state_change and old_state != new_state:
            self._on_state_change(old_state, new_state)

    def reset(self):
        with self._lock:
            self._set_state(self.STATE_CLOSED)
            self._failure_count = 0
            self._half_open_calls = 0

    def stats(self):
        return {
            "state": self._state,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self._last_failure_time,
        }


class CircuitBreakerRegistry:
    """熔断器注册表"""

    def __init__(self):
        self._breakers = {}
        self._lock = threading.Lock()

    def get_or_create(self, name, **kwargs):
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(**kwargs)
            return self._breakers[name]

    def get(self, name):
        return self._breakers.get(name)

    def reset_all(self):
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()

    def stats_all(self):
        return {name: cb.stats() for name, cb in self._breakers.items()}
