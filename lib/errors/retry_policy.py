# -*- coding: utf-8 -*-
"""重试策略 —— 多种退避算法与重试控制"""

import random
import time


class RetryPolicy:
    """重试策略基类"""

    def __init__(self, max_retries=3, retryable_exceptions=None):
        self.max_retries = max_retries
        self.retryable_exceptions = retryable_exceptions or (Exception,)

    def get_delay(self, attempt):
        raise NotImplementedError

    def is_retryable(self, exception):
        return isinstance(exception, self.retryable_exceptions)

    def should_retry(self, attempt, exception):
        if attempt >= self.max_retries:
            return False
        return self.is_retryable(exception)


class FixedIntervalRetry(RetryPolicy):
    """固定间隔重试"""

    def __init__(self, interval=1.0, **kwargs):
        super().__init__(**kwargs)
        self.interval = interval

    def get_delay(self, attempt):
        return self.interval


class ExponentialBackoffRetry(RetryPolicy):
    """指数退避重试"""

    def __init__(self, base_delay=1.0, max_delay=60.0, jitter=True, **kwargs):
        super().__init__(**kwargs)
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def get_delay(self, attempt):
        delay = min(self.max_delay, self.base_delay * (2 ** attempt))
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        return delay


class LinearBackoffRetry(RetryPolicy):
    """线性退避重试"""

    def __init__(self, increment=2.0, max_delay=30.0, **kwargs):
        super().__init__(**kwargs)
        self.increment = increment
        self.max_delay = max_delay

    def get_delay(self, attempt):
        return min(self.max_delay, self.increment * (attempt + 1))


class RetryExecutor:
    """重试执行器"""

    def __init__(self, policy=None):
        self.policy = policy or ExponentialBackoffRetry()

    def execute(self, fn, *args, **kwargs):
        last_exception = None
        for attempt in range(self.policy.max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if not self.policy.should_retry(attempt, e):
                    raise
                delay = self.policy.get_delay(attempt)
                if delay > 0:
                    time.sleep(delay)
        raise last_exception

    def execute_with_callback(self, fn, on_retry=None, *args, **kwargs):
        last_exception = None
        for attempt in range(self.policy.max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if not self.policy.should_retry(attempt, e):
                    raise
                delay = self.policy.get_delay(attempt)
                if on_retry:
                    on_retry(attempt, e, delay)
                if delay > 0:
                    time.sleep(delay)
        raise last_exception
