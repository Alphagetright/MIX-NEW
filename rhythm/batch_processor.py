# -*- coding: utf-8 -*-
"""
古典诗词音韵格律分析引擎 — 批量分析管线
========================================
支持目录批量扫描、并发分析、进度回调和结果汇总。
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Set

from .errors import AnalysisError, FileSystemError, safe_call
from .logger import get_logger, LoggerMixin
from .models import BatchResult, ScansionResult
from .scansion_engine import ScansionEngine

logger = get_logger("batch_processor")


class BatchProcessor(LoggerMixin):
    """批量分析管线"""

    def __init__(self, engine: ScansionEngine = None, max_workers: int = 4):
        self._engine = engine or ScansionEngine()
        self._max_workers = max_workers

    # ─── 列表处理 ───

    def run_list(
        self,
        poems: List[Dict[str, Any]],
        form: str = None,
        progress_callback: Callable = None,
    ) -> BatchResult:
        """批量分析诗歌列表

        Args:
            poems: List of {"title", "author", "lines"/"text"}
            form: 指定体裁
            progress_callback: 进度回调 (processed, total) -> None

        Returns:
            BatchResult
        """
        n = len(poems)
        result = BatchResult(total_poems=n)
        start = time.time()

        for i, poem in enumerate(poems):
            result.processed += 1
            try:
                title = poem.get("title", poem.get("标题", ""))
                author = poem.get("author", poem.get("作者", ""))
                lines = poem.get("lines", poem.get("诗句", []))
                text = poem.get("text", poem.get("原文", ""))

                if not lines and text:
                    from .data_loader import extract_chinese_lines
                    lines = extract_chinese_lines(text)

                if not lines:
                    raise AnalysisError(f"无法提取诗句: {title}")

                scan_result = self._engine.scan(lines, form=form)
                scan_result.poem_title = title
                scan_result.poem_author = author
                result.results.append(scan_result)
                result.succeeded += 1

            except Exception as e:
                result.failed += 1
                result.errors.append({
                    "poem": poem.get("title", f"第{i+1}首"),
                    "error": str(e),
                })
                logger.warning(f"分析失败 ({i+1}/{n}): {e}")

            if progress_callback:
                progress_callback(result.processed, n)

        result.duration_seconds = round(time.time() - start, 2)
        logger.info(
            f"批量完成: {result.succeeded}/{n}成功, "
            f"{result.failed}失败, 耗时{result.duration_seconds}秒"
        )
        return result

    # ─── 目录处理 ───

    def run_directory(
        self,
        dir_path: str,
        extensions: List[str] = None,
        form: str = None,
    ) -> BatchResult:
        """批量分析目录下所有诗歌"""
        from .data_loader import load_poems_from_directory

        poems_meta = load_poems_from_directory(dir_path, extensions)
        poems_dicts = [
            {
                "title": p.title,
                "author": p.author,
                "lines": p.lines,
                "text": p.text,
            }
            for p in poems_meta
        ]

        return self.run_list(poems_dicts, form=form)

    # ─── 并发处理 ───

    def run_concurrent(
        self,
        poems: List[Dict[str, Any]],
        max_workers: int = None,
        form: str = None,
    ) -> BatchResult:
        """并发批量分析"""
        max_workers = max_workers or self._max_workers
        n = len(poems)
        result = BatchResult(total_poems=n)
        start = time.time()

        def _scan_one(item):
            try:
                title = item.get("title", "")
                lines = item.get("lines", [])
                if not lines:
                    text = item.get("text", "")
                    from .data_loader import extract_chinese_lines
                    lines = extract_chinese_lines(text)
                if not lines:
                    return None, f"无法提取诗句: {title}"
                sr = self._engine.scan(lines, form=form)
                sr.poem_title = title
                sr.poem_author = item.get("author", "")
                return sr, None
            except Exception as e:
                return None, str(e)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_scan_one, p) for p in poems]
            for future in as_completed(futures):
                result.processed += 1
                sr, err = future.result()
                if err:
                    result.failed += 1
                else:
                    result.results.append(sr)
                    result.succeeded += 1

        result.duration_seconds = round(time.time() - start, 2)
        return result

    # ─── 汇总 ───

    def to_summary(self, result: BatchResult) -> Dict[str, Any]:
        """批量汇总统计"""
        forms = {}
        scores = []
        top_yunbus = {}

        for sr in result.results:
            if sr.form:
                forms[sr.form] = forms.get(sr.form, 0) + 1
            scores.append(sr.overall_score)
            if sr.rhyme_report and sr.rhyme_report.rhyme_yunbu:
                yb = sr.rhyme_report.rhyme_yunbu
                top_yunbus[yb] = top_yunbus.get(yb, 0) + 1

        avg_score = sum(scores) / max(1, len(scores))
        top_forms = sorted(forms.items(), key=lambda x: -x[1])[:5]
        top_ybs = sorted(top_yunbus.items(), key=lambda x: -x[1])[:5]

        return {
            "total": result.total_poems,
            "succeeded": result.succeeded,
            "failed": result.failed,
            "success_rate": result.success_rate,
            "avg_score": round(avg_score, 1),
            "duration_seconds": result.duration_seconds,
            "top_forms": [{"form": f, "count": c} for f, c in top_forms],
            "top_yunbus": [{"yunbu": y, "count": c} for y, c in top_ybs],
            "errors": len(result.errors),
        }
