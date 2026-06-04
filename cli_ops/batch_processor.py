# -*- coding: utf-8 -*-
"""
批量数据处理引擎
================
支持并发批量任务执行，包含：任务调度、并行处理、进度追踪、超时控制、
失败重试、结果汇总。

特性：
  - ThreadPoolExecutor 并发执行
  - 可配置最大工作线程数
  - 单个任务超时控制
  - 失败自动重试
  - 实时进度回调
  - 结果汇总与统计
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .config import (
    BATCH_PROCESSOR_MAX_WORKERS,
    BATCH_PROCESSOR_CHUNK_SIZE,
    BATCH_PROCESSOR_TIMEOUT,
)
from .logger import get_logger
from .models import BatchTask, BatchResult

logger = get_logger("batch_processor")


class BatchProcessor:
    """
    批量任务处理器

    支持并发执行大量同类任务，自动管理线程池、超时和重试。

    Usage:
        bp = BatchProcessor(max_workers=4)
        tasks = [{"name": f"task_{i}", "command": process_file, "args": {"path": p}} for i, p in enumerate(files)]
        result = bp.run(tasks)
        print(f"完成: {result.completed}/{result.total}, 成功率: {result.success_rate}%")
    """

    def __init__(self, max_workers: int = BATCH_PROCESSOR_MAX_WORKERS,
                 chunk_size: int = BATCH_PROCESSOR_CHUNK_SIZE,
                 default_timeout: int = BATCH_PROCESSOR_TIMEOUT):
        self._max_workers = max_workers
        self._chunk_size = chunk_size
        self._default_timeout = default_timeout
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None
        self._lock = threading.Lock()
        self._completed_count = 0
        self._total_count = 0
        logger.info(f"BatchProcessor 初始化: workers={max_workers}, chunk={chunk_size}")

    def on_progress(self, callback: Callable[[int, int, str], None]) -> None:
        """
        注册进度回调

        回调参数: (completed, total, status_message)
        """
        self._progress_callback = callback

    def run(self, tasks: List[Dict[str, Any]],
            timeout: Optional[int] = None,
            stop_on_first_error: bool = False) -> BatchResult:
        """
        执行批量任务

        参数:
            tasks: 任务配置列表 [{"name": str, "command": callable, "args": dict}, ...]
            timeout: 单个任务超时（秒），None 使用默认值
            stop_on_first_error: 是否在首个错误时停止

        返回:
            BatchResult: 执行结果汇总
        """
        result = BatchResult(
            total=len(tasks),
            started_at=time.time(),
        )

        if not tasks:
            result.completed_at = time.time()
            return result

        self._total_count = len(tasks)
        self._completed_count = 0

        timeout_val = timeout if timeout is not None else self._default_timeout

        batch_tasks = []
        for t_info in tasks:
            task = BatchTask(
                name=t_info.get("name", "unnamed"),
                command=str(t_info.get("command", "")),
                args=t_info.get("args", {}),
                max_retries=t_info.get("max_retries", 3),
            )
            batch_tasks.append(task)

        result.tasks = batch_tasks

        # 分块执行
        chunks = [batch_tasks[i:i + self._chunk_size]
                  for i in range(0, len(batch_tasks), self._chunk_size)]

        for chunk_idx, chunk in enumerate(chunks):
            logger.info(f"批处理: 第 {chunk_idx + 1}/{len(chunks)} 块 ({len(chunk)} 个任务)")

            with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                futures = {}
                for task in chunk:
                    future = executor.submit(self._execute_task, task, timeout_val)
                    futures[future] = task

                for future in futures:
                    task = futures[future]
                    try:
                        task_result = future.result(timeout=timeout_val * 2)
                        task.status = "completed"
                        task.result = task_result
                        task.completed_at = time.time()
                        result.completed += 1
                    except FutureTimeoutError:
                        task.status = "timeout"
                        task.error = f"任务超时 ({timeout_val}s)"
                        result.timeout += 1
                        logger.warning(f"批处理超时: {task.name}")
                        if stop_on_first_error:
                            break
                    except Exception as e:
                        task.status = "failed"
                        task.error = str(e)
                        result.failed += 1
                        logger.error(f"批处理失败 [{task.name}]: {e}")
                        if stop_on_first_error:
                            break

                    self._completed_count += 1
                    if self._progress_callback:
                        try:
                            self._progress_callback(
                                self._completed_count,
                                self._total_count,
                                task.status,
                            )
                        except Exception:
                            pass

        result.completed_at = time.time()
        duration = result.total_duration
        logger.info(
            f"批处理完成: {result.completed}/{result.total} 成功, "
            f"{result.failed} 失败, {result.timeout} 超时, "
            f"耗时 {duration}s, 成功率 {result.success_rate}%"
        )
        return result

    def _execute_task(self, task: BatchTask, timeout: int) -> Any:
        """执行单个任务（含重试）"""
        task.status = "running"
        task.started_at = time.time()

        last_error = None
        for attempt in range(task.max_retries + 1):
            try:
                if isinstance(task.command, str):
                    # 字符串命令通过 subprocess 执行
                    import subprocess
                    proc = subprocess.run(
                        task.command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )
                    if proc.returncode != 0:
                        raise RuntimeError(f"命令返回非零: {proc.returncode} stderr={proc.stderr[:200]}")
                    return {"stdout": proc.stdout[:1000], "stderr": proc.stderr[:500], "returncode": proc.returncode}
                elif callable(task.command):
                    return task.command(**task.args)
                else:
                    raise ValueError(f"不支持的命令类型: {type(task.command)}")
            except Exception as e:
                last_error = e
                task.retry_count = attempt
                if attempt < task.max_retries:
                    wait = 2 ** attempt  # 指数退避
                    logger.debug(f"任务 {task.name} 重试 {attempt + 1}/{task.max_retries} (等待 {wait}s)")
                    time.sleep(wait)

        raise last_error or RuntimeError("任务执行失败")


# ============================================================================
# 便捷函数
# ============================================================================


def run_parallel(func: Callable, items: List[Any],
                 max_workers: int = BATCH_PROCESSOR_MAX_WORKERS,
                 timeout: int = BATCH_PROCESSOR_TIMEOUT,
                 progress_label: str = "处理中") -> BatchResult:
    """
    对列表中的每个元素并行执行函数

    参数:
        func: 要并行执行的函数 (item) -> Any
        items: 输入列表
        max_workers: 最大并发数
        timeout: 单个任务超时
        progress_label: 进度标签

    返回:
        BatchResult: 执行结果
    """
    tasks = [
        {"name": f"{progress_label}_{i}", "command": func, "args": {"item": item}}
        for i, item in enumerate(items)
    ]
    bp = BatchProcessor(max_workers=max_workers)
    return bp.run(tasks, timeout=timeout)


def run_map(func: Callable, items: List[Any],
            max_workers: int = BATCH_PROCESSOR_MAX_WORKERS) -> List[Any]:
    """
    并行 map：对列表每个元素并行执行函数，返回结果列表

    参数:
        func: 映射函数
        items: 输入列表
        max_workers: 最大并发数

    返回:
        List: 结果列表（与输入顺序一致，失败项为 None）
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = [None] * len(items)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(func, item): idx for idx, item in enumerate(items)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result(timeout=BATCH_PROCESSOR_TIMEOUT)
            except Exception as e:
                logger.error(f"并行 map 失败 [{idx}]: {e}")
                results[idx] = None
    return results


def chunked_process(items: List[Any], process_func: Callable[[List[Any]], List[Any]],
                    chunk_size: int = BATCH_PROCESSOR_CHUNK_SIZE,
                    max_workers: int = BATCH_PROCESSOR_MAX_WORKERS) -> List[Any]:
    """
    分块并行处理

    将大列表分块，每块在独立线程中处理，最后合并结果。

    参数:
        items: 输入列表
        process_func: 处理函数，接收列表返回列表
        chunk_size: 每块大小
        max_workers: 最大并发数

    返回:
        List: 合并后的结果列表
    """
    chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
    logger.info(f"分块处理: {len(items)} 条 → {len(chunks)} 块")

    all_results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_func, chunk) for chunk in chunks]
        for i, future in enumerate(futures):
            try:
                chunk_result = future.result(timeout=BATCH_PROCESSOR_TIMEOUT)
                all_results.extend(chunk_result if chunk_result else [])
            except Exception as e:
                logger.error(f"分块处理失败 [{i}]: {e}")

    return all_results


def retry_on_failure(func: Callable, max_retries: int = 3, delay: float = 1.0,
                     backoff: float = 2.0, exceptions: tuple = (Exception,)) -> Any:
    """
    失败重试装饰器（函数版本）

    参数:
        func: 要重试的函数
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 延迟倍增因子
        exceptions: 需要重试的异常类型

    返回:
        函数返回值（成功时）
    """
    last_error = None
    current_delay = delay
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_error = e
            if attempt < max_retries:
                logger.debug(f"重试 {attempt + 1}/{max_retries} (等待 {current_delay:.1f}s): {e}")
                time.sleep(current_delay)
                current_delay *= backoff
    raise last_error or RuntimeError("重试耗尽")
