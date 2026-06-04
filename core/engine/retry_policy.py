# -*- coding: utf-8 -*-
"""引擎重试策略 —— 推理调用专用重试控制"""

import time
import random


class RetryableError(Exception):
    """可重试异常基类"""
    pass


class RateLimitError(RetryableError):
    """速率限制错误"""
    def __init__(self, message="Rate limit exceeded", retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class ServerOverloadError(RetryableError):
    """服务过载错误"""
    def __init__(self, message="Server overloaded", status_code=503):
        super().__init__(message)
        self.status_code = status_code


class TokenLimitError(RetryableError):
    """Token限制错误"""
    def __init__(self, message="Token limit exceeded", limit=None):
        super().__init__(message)
        self.limit = limit


class TimeoutError(RetryableError):
    """超时错误"""
    pass


class RetryPolicy:
    """引擎重试策略"""

    def __init__(self, max_retries=3, base_delay=1.0, max_delay=60.0,
                 use_jitter=True, retryable_errors=None):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.use_jitter = use_jitter
        self.retryable_errors = retryable_errors or (
            RetryableError, ConnectionError, TimeoutError
        )

    def compute_delay(self, attempt):
        delay = min(self.max_delay, self.base_delay * (2 ** attempt))
        if self.use_jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        return delay

    def is_retryable(self, exception):
        return isinstance(exception, self.retryable_errors)

    def should_retry(self, attempt, exception):
        if attempt >= self.max_retries:
            return False
        return self.is_retryable(exception)

    def get_retry_after(self, exception):
        if isinstance(exception, RateLimitError) and exception.retry_after:
            return exception.retry_after
        return None


class RetryContext:
    """重试上下文"""

    def __init__(self, policy=None):
        self.policy = policy or RetryPolicy()
        self.attempt = 0
        self.delays = []
        self.errors = []

    def next_delay(self, exception):
        retry_after = self.policy.get_retry_after(exception)
        if retry_after is not None:
            delay = retry_after
        else:
            delay = self.policy.compute_delay(self.attempt)
        self.delays.append(delay)
        return delay

    def record_error(self, exception):
        self.errors.append((self.attempt, exception))

    def increment(self):
        self.attempt += 1

    @property
    def exhausted(self):
        return self.attempt >= self.policy.max_retries

    @property
    def last_error(self):
        if self.errors:
            return self.errors[-1][1]
        return None

    def reset(self):
        self.attempt = 0
        self.delays.clear()
        self.errors.clear()


class RetryExecutor:
    """重试执行器"""

    def __init__(self, policy=None):
        self.policy = policy or RetryPolicy()

    def execute(self, fn, *args, **kwargs):
        context = RetryContext(self.policy)
        while not context.exhausted:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                context.record_error(e)
                if not context.policy.should_retry(context.attempt, e):
                    raise
                delay = context.next_delay(e)
                context.increment()
                if delay > 0:
                    time.sleep(delay)
        if context.last_error:
            raise context.last_error

    def execute_async(self, fn, callback=None, *args, **kwargs):
        context = RetryContext(self.policy)
        while not context.exhausted:
            try:
                result = fn(*args, **kwargs)
                if callback:
                    callback(context.attempt, result, None)
                return result
            except Exception as e:
                context.record_error(e)
                if callback:
                    callback(context.attempt, None, e)
                if not context.policy.should_retry(context.attempt, e):
                    raise
                delay = context.next_delay(e)
                context.increment()
                if delay > 0:
                    time.sleep(delay)
        if context.last_error:
            raise context.last_error


class RetryPolicyBuilder:
    """重试策略构建器"""

    def __init__(self):
        self.max_retries = 3
        self.base_delay = 1.0
        self.max_delay = 60.0
        self.use_jitter = True
        self.retryable_errors = None

    def with_max_retries(self, n):
        self.max_retries = n
        return self

    def with_base_delay(self, delay):
        self.base_delay = delay
        return self

    def with_max_delay(self, delay):
        self.max_delay = delay
        return self

    def with_jitter(self, enabled=True):
        self.use_jitter = enabled
        return self

    def with_retryable_errors(self, errors):
        self.retryable_errors = errors
        return self

    def build(self):
        return RetryPolicy(
            max_retries=self.max_retries,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            use_jitter=self.use_jitter,
            retryable_errors=self.retryable_errors,
        )
