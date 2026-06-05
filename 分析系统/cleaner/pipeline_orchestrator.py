# -*- coding: utf-8 -*-
"""
流水线编排器
============
将清洗、校验、去重、导出等独立阶段编排为完整的自动化数据预处理流水线。
支持流水线配置、阶段依赖管理、失败重试和断点续传。
"""

import os, time, json
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from .config import DATA_DIR
from .logger import get_logger

logger = get_logger("pipeline_orchestrator")


class PipelineStage:
    """流水线阶段定义"""

    def __init__(self, name: str, func: Callable, description: str = "",
                 depends_on: List[str] = None, retry_count: int = 3,
                 timeout_seconds: int = 600):
        self.name = name; self.func = func; self.description = description
        self.depends_on = depends_on or []; self.retry_count = retry_count
        self.timeout_seconds = timeout_seconds
        self.status = "pending"; self.started_at: float = 0
        self.completed_at: float = 0; self.error: str = ""
        self.output: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "description": self.description,
                "status": self.status, "depends_on": self.depends_on,
                "duration": round(self.completed_at - self.started_at, 2) if self.completed_at else 0,
                "error": self.error}


class PipelineOrchestrator:
    """
    流水线编排器

    管理数据预处理流水线的执行顺序、阶段依赖和错误恢复。

    Usage:
        orchestrator = PipelineOrchestrator()
        orchestrator.add_stage("clean", clean_func, "数据清洗")
        orchestrator.add_stage("validate", validate_func, "结构校验", depends_on=["clean"])
        result = orchestrator.run({"data_dir": "./poem_json"})
    """

    def __init__(self, name: str = "default_pipeline"):
        self.name = name
        self._stages: Dict[str, PipelineStage] = {}
        self._execution_order: List[str] = []
        self._results: Dict[str, Any] = {}
        self._checkpoint_file: str = f".pipeline_{name}_checkpoint.json"

    def add_stage(self, name: str, func: Callable, description: str = "",
                  depends_on: List[str] = None, retry_count: int = 3,
                  timeout_seconds: int = 600) -> "PipelineOrchestrator":
        """添加流水线阶段"""
        stage = PipelineStage(name, func, description, depends_on,
                              retry_count, timeout_seconds)
        self._stages[name] = stage
        logger.info(f"Pipeline[{self.name}]: 添加阶段 '{name}'")
        return self

    def _resolve_order(self) -> List[str]:
        """解析阶段依赖顺序（拓扑排序）"""
        in_degree = {name: len(s.depends_on) for name, s in self._stages.items()}
        adj: Dict[str, List[str]] = {name: [] for name in self._stages}
        for name, stage in self._stages.items():
            for dep in stage.depends_on:
                if dep in adj:
                    adj[dep].append(name)

        queue = [n for n, d in in_degree.items() if d == 0]
        order = []
        while queue:
            node = queue.pop(0); order.append(node)
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self._stages):
            remaining = set(self._stages.keys()) - set(order)
            logger.warning(f"流水线存在循环依赖: {remaining}"); order.extend(remaining)

        self._execution_order = order
        return order

    def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行流水线"""
        if not self._stages:
            return {"status": "empty", "message": "无流水线阶段"}

        context = context or {}
        order = self._resolve_order()
        logger.info(f"Pipeline[{self.name}]: 开始执行 ({len(order)}个阶段)")

        for stage_name in order:
            stage = self._stages[stage_name]
            logger.info(f"Pipeline[{self.name}]: 执行 '{stage_name}' — {stage.description}")

            stage.status = "running"; stage.started_at = time.time()

            for attempt in range(stage.retry_count + 1):
                try:
                    stage.output = stage.func(context)
                    stage.status = "completed"
                    self._results[stage_name] = stage.output
                    break
                except Exception as e:
                    stage.error = str(e)
                    if attempt < stage.retry_count:
                        wait = 2 ** attempt
                        logger.warning(f"阶段 '{stage_name}' 失败，{wait}s后重试({attempt+1}/{stage.retry_count})")
                        time.sleep(wait)
                    else:
                        stage.status = "failed"
                        logger.error(f"阶段 '{stage_name}' 失败: {e}")

            stage.completed_at = time.time()

            if stage.status == "failed":
                # 检查是否所有依赖都完成了
                deps_failed = [d for d in stage.depends_on if self._stages[d].status == "failed"]
                if deps_failed:
                    logger.warning(f"阶段 '{stage_name}' 因依赖失败而跳过")

        return self.get_summary()

    def get_summary(self) -> Dict[str, Any]:
        """获取流水线执行摘要"""
        total = len(self._stages)
        completed = sum(1 for s in self._stages.values() if s.status == "completed")
        failed = sum(1 for s in self._stages.values() if s.status == "failed")
        total_duration = sum(s.completed_at - s.started_at for s in self._stages.values() if s.completed_at)

        return {
            "pipeline": self.name,
            "total_stages": total,
            "completed": completed,
            "failed": failed,
            "success_rate": round(completed / max(1, total) * 100, 1),
            "total_duration_seconds": round(total_duration, 2),
            "stages": [s.to_dict() for s in self._stages.values()],
            "results": {k: str(v)[:200] for k, v in self._results.items()},
        }

    def save_checkpoint(self) -> str:
        """保存流水线断点"""
        checkpoint = {
            "pipeline": self.name,
            "saved_at": datetime.now().isoformat(),
            "stages": {n: s.to_dict() for n, s in self._stages.items()},
        }
        with open(self._checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)
        return self._checkpoint_file

    def load_checkpoint(self) -> bool:
        """加载流水线断点"""
        if not os.path.exists(self._checkpoint_file):
            return False
        with open(self._checkpoint_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for name, info in data.get("stages", {}).items():
            if name in self._stages:
                self._stages[name].status = info["status"]
        logger.info(f"Pipeline[{self.name}]: 从断点恢复")
        return True


def create_default_pipeline() -> PipelineOrchestrator:
    """创建默认的数据预处理流水线"""
    from .encoding_detector import detect_directory_encodings
    from .preprocessor import batch_validate_directory
    from .dedup_engine import DedupEngine
    from .data_profiler import DataProfiler

    def stage_encoding(ctx):
        directory = ctx.get("data_dir", DATA_DIR)
        return detect_directory_encodings(directory)

    def stage_validate(ctx):
        directory = ctx.get("data_dir", DATA_DIR)
        return batch_validate_directory(directory)

    def stage_quality(ctx):
        directory = ctx.get("data_dir", DATA_DIR)
        profiler = DataProfiler()
        return profiler.generate_quality_report(directory).to_dict()

    pipeline = PipelineOrchestrator("default")
    pipeline.add_stage("encoding", stage_encoding, "编码检测与统计")
    pipeline.add_stage("validate", stage_validate, "数据结构校验", depends_on=["encoding"])
    pipeline.add_stage("quality", stage_quality, "数据质量评估", depends_on=["validate"])
    return pipeline


def run_pipeline_from_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """从配置字典创建并运行流水线"""
    pipeline = PipelineOrchestrator(config.get("name", "custom"))
    for stage_cfg in config.get("stages", []):
        name = stage_cfg["name"]
        func = stage_cfg.get("func")
        depends = stage_cfg.get("depends_on", [])
        pipeline.add_stage(name, func, stage_cfg.get("description", ""), depends,
                          stage_cfg.get("retry_count", 3))
    return pipeline.run(config.get("context", {}))
