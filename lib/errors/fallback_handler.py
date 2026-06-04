# -*- coding: utf-8 -*-
"""降级处理 —— 失败时的降级与备选策略"""


class FallbackHandler:
    """降级处理器 —— 策略链"""

    def __init__(self):
        self._strategies = []

    def add_strategy(self, strategy):
        self._strategies.append(strategy)

    def execute(self, fn, fallback_fn=None, default=None):
        try:
            return fn()
        except Exception:
            if fallback_fn:
                try:
                    return fallback_fn()
                except Exception:
                    return default
            return default

    def execute_chain(self, fns, context=None):
        """依次尝试多个函数，直到成功"""
        last_error = None
        for fn in fns:
            try:
                return fn(context) if context else fn()
            except Exception as e:
                last_error = e
                continue
        raise last_error


class DefaultValueStrategy:
    """默认值降级策略"""

    def __init__(self, default_value):
        self.default_value = default_value

    def execute(self, fn):
        try:
            return fn()
        except Exception:
            return self.default_value


class CacheFallbackStrategy:
    """缓存降级策略 —— 失败时返回缓存数据"""

    def __init__(self, cache, key):
        self.cache = cache
        self.key = key

    def execute(self, fn):
        try:
            result = fn()
            self.cache.set(self.key, result)
            return result
        except Exception:
            return self.cache.get(self.key)


class EmptyResultStrategy:
    """空结果降级策略"""

    def __init__(self, empty_factory=None):
        self.empty_factory = empty_factory or (lambda: None)

    def execute(self, fn):
        try:
            return fn()
        except Exception:
            return self.empty_factory()


class GracefulDegrader:
    """优雅降级器 —— 统合多种降级策略"""

    def __init__(self, fallback_handler=None):
        self.fallback = fallback_handler or FallbackHandler()
        self._config = {}

    def register_strategy(self, operation, strategy):
        self._config[operation] = strategy

    def call(self, operation, fn):
        strategy = self._config.get(operation)
        if strategy:
            return strategy.execute(fn)
        return self.fallback.execute(fn)
