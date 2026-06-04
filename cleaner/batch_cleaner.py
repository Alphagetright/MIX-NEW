# -*- coding: utf-8 -*-
"""
批量清洗引擎
============
提供完整的批量数据清洗流水线：扫描 → 编码检测 → 清洗 → 解析 → 校验 → 去重 → 导出。
"""

import os, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import DATA_DIR, EXPORT_DIR, BATCH_MAX_WORKERS, BATCH_TIMEOUT, PREPROC_MAX_ERRORS
from .logger import get_logger
from .models import CleaningResult, BatchReport

logger = get_logger("batch_cleaner")


class BatchCleaner:
    """
    批量清洗流水线

    对目录中的所有JSON文件执行完整的清洗流水线。

    Usage:
        cleaner = BatchCleaner()
        report = cleaner.run_pipeline("./poem_json")
        print(f"成功率: {report.success_rate}%")
    """

    def __init__(self, max_workers: int = None):
        self._max_workers = max_workers or BATCH_MAX_WORKERS

    def run_pipeline(self, directory: str = None,
                     stages: List[str] = None) -> BatchReport:
        """
        执行批量清洗流水线

        参数:
            directory: 目标目录
            stages: 要执行的阶段列表 ["encode", "clean", "parse", "validate", "dedup"]

        返回:
            BatchReport: 批量处理报告
        """
        if directory is None: directory = DATA_DIR
        if stages is None: stages = ["clean", "parse", "validate"]

        from .utils import list_files
        files = list_files(directory, extensions=[".json", ".txt"], recursive=True)

        report = BatchReport(total_files=len(files))

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {executor.submit(self._process_file, fp, stages): fp for fp in files}
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=BATCH_TIMEOUT)
                    report.results.append(result)
                    report.processed += 1
                    if result.success: report.succeeded += 1
                    else: report.failed += 1
                    report.total_fixes += result.fix_count
                    report.total_errors += result.error_count
                    if result.encoding_detected:
                        enc = result.encoding_detected
                        report.encoding_distribution[enc] = report.encoding_distribution.get(enc, 0) + 1
                except Exception as e:
                    report.failed += 1; report.processed += 1
                    logger.error(f"批处理任务异常: {e}")

        report.completed_at = time.time()
        logger.info(f"批量清洗完成: {report.succeeded}/{report.total_files}成功, "
                     f"耗时{report.duration_seconds}s")
        return report

    def _process_file(self, file_path: str, stages: List[str]) -> CleaningResult:
        """处理单个文件"""
        start = time.time()
        result = CleaningResult(file_path=file_path, file_name=os.path.basename(file_path))

        from .encoding_detector import detect_encoding
        from .preprocessor import safe_parse_json, clean_json_content

        try:
            # 编码检测
            enc, conf = detect_encoding(file_path)
            result.encoding_detected = enc
            result.encoding_original = enc

            # 读取
            with open(file_path, "rb") as f:
                raw_bytes = f.read()
            result.original_size = len(raw_bytes)

            # 清洗
            if "clean" in stages:
                raw_text = raw_bytes.decode(enc if enc != "unknown" else "utf-8", errors="replace")
                cleaned, fixes = clean_json_content(raw_text)
                result.fixes_applied = fixes
                result.fix_count = len(fixes)

            # 解析
            if "parse" in stages:
                data, errors = safe_parse_json(file_path)
                if data is not None:
                    result.parse_success = True
                else:
                    result.errors = errors
                    result.error_count = len(errors)

            # 校验
            if "validate" in stages and result.parse_success:
                from .preprocessor import validate_poem_structure, extract_poems
                data, _ = safe_parse_json(file_path)
                if data:
                    poems = extract_poems(data)
                    for poem in poems:
                        ok, issues = validate_poem_structure(poem)
                        if not ok:
                            result.errors.extend(issues)
                            result.error_count += len(issues)

        except Exception as e:
            result.errors.append(str(e))
            result.error_count += 1

        result.duration_ms = round((time.time() - start) * 1000)
        return result

    def export_clean_data(self, report: BatchReport, output_dir: str = None) -> str:
        """将清洗成功的文件导出到新目录"""
        if output_dir is None:
            output_dir = os.path.join(EXPORT_DIR, f"cleaned_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(output_dir, exist_ok=True)

        count = 0
        for r in report.results:
            if r.success and os.path.exists(r.file_path):
                import shutil
                dst = os.path.join(output_dir, r.file_name)
                shutil.copy2(r.file_path, dst)
                count += 1

        logger.info(f"导出清洗数据: {count}文件 → {output_dir}")
        return output_dir


def quick_clean_file(file_path: str) -> CleaningResult:
    """快速清洗单个文件"""
    cleaner = BatchCleaner(max_workers=1)
    return cleaner._process_file(file_path, ["clean", "parse"])


# ─── 增量清洗 ───

class IncrementalCleaner:
    """增量清洗器——仅处理变更的文件"""

    def __init__(self, cache_file: str = ".cleaner_cache.json"):
        self._cache_file = cache_file
        self._cache: Dict[str, float] = {}; self._load_cache()

    def _load_cache(self):
        if os.path.exists(self._cache_file):
            try:
                with open(self._cache_file, "r") as f: self._cache = json.load(f)
            except: self._cache = {}

    def _save_cache(self):
        with open(self._cache_file, "w") as f: json.dump(self._cache, f)

    def find_changed_files(self, directory: str) -> List[str]:
        from .utils import list_files
        files = list_files(directory, extensions=[".json", ".txt"], recursive=True)
        changed = []
        for fp in files:
            mtime = os.path.getmtime(fp)
            if fp not in self._cache or self._cache[fp] < mtime:
                changed.append(fp); self._cache[fp] = mtime
        self._save_cache()
        return changed

    def process_changed(self, directory: str) -> BatchReport:
        changed = self.find_changed_files(directory)
        logger.info(f"增量检测: {len(changed)} 个文件已变更")
        if not changed:
            return BatchReport(total_files=0)
        cleaner = BatchCleaner()
        report = BatchReport(total_files=len(changed))
        for fp in changed:
            result = cleaner._process_file(fp, ["clean", "parse", "validate"])
            report.results.append(result); report.processed += 1
            if result.success: report.succeeded += 1
            else: report.failed += 1
        report.completed_at = time.time()
        return report


class PipelineBuilder:
    """流水线构建器——自定义清洗流水线"""

    def __init__(self):
        self._stages: List[Tuple[str, callable]] = []

    def add_stage(self, name: str, func: callable) -> "PipelineBuilder":
        self._stages.append((name, func)); return self

    def run(self, data: Any) -> Dict[str, Any]:
        results = {"stages": []}
        current = data
        for name, func in self._stages:
            try:
                current = func(current)
                results["stages"].append({"name": name, "status": "success"})
            except Exception as e:
                results["stages"].append({"name": name, "status": "failed", "error": str(e)})
                return results
        results["result"] = current; results["success"] = True; return results

    @classmethod
    def default_pipeline(cls) -> "PipelineBuilder":
        from .preprocessor import clean_json_content, validate_poem_structure
        builder = cls()
        builder.add_stage("clean", lambda d: clean_json_content(json.dumps(d, ensure_ascii=False))[0])
        builder.add_stage("parse", lambda d: (json.loads(d) if isinstance(d, str) else d, []))
        builder.add_stage("validate", lambda d: validate_poem_structure(d[0] if isinstance(d, tuple) else d))
        return builder


def estimate_cleaning_time(file_count: int, avg_file_size_mb: float = 1.0) -> Dict[str, float]:
    """估算清洗耗时"""
    time_per_file = 0.05 + avg_file_size_mb * 0.02  # 基础50ms + 每MB 20ms
    total = file_count * time_per_file
    return {"estimated_seconds": round(total, 1), "estimated_minutes": round(total / 60, 1),
            "file_count": file_count, "recommended_workers": min(8, max(1, file_count // 20))}
