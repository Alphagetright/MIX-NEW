# -*- coding: utf-8 -*-
"""
古典诗词音韵格律分析引擎 — 多格式分析报告生成
==============================================
支持Text/JSON/HTML/CSV四种格式的格律分析报告输出，
可将报告保存到文件。
"""
import csv
import json
import os
from typing import Any, Dict, List, Optional

from .errors import ExportError, safe_call
from .logger import get_logger
from .models import BatchResult, ScansionResult
from .tone_visualizer import ToneVisualizer
from .utils import safe_json_dumps, sanitize_filename

logger = get_logger("report_generator")


class ReportGenerator:
    """分析报告生成器"""

    def __init__(self):
        self._visualizer = ToneVisualizer()

    # ─── Text 格式 ───

    def generate_text_report(self, result: ScansionResult) -> str:
        """生成文本格式分析报告"""
        return self._visualizer.to_text(result)

    # ─── JSON 格式 ───

    def generate_json_report(self, result: ScansionResult) -> str:
        """生成JSON格式分析报告"""
        return safe_json_dumps(result.to_dict(), indent=2)

    # ─── HTML 格式 ───

    def generate_html_report(self, result: ScansionResult) -> str:
        """生成HTML分析报告"""
        return self._visualizer.to_html(result)

    # ─── CSV 格式 ───

    def generate_csv_report(self, results: List[ScansionResult]) -> str:
        """生成CSV格式分析汇总"""
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "标题", "作者", "体裁", "起式", "句数", "字数",
            "合规率", "格律判定", "违规数", "孤平句",
            "三平调句", "三仄尾句",
            "主押韵部", "合韵", "邻韵通押",
            "平声", "仄声", "入声", "未知",
            "对仗评分", "综合评分",
        ])

        for r in results:
            mr = r.meter_report
            rr = r.rhyme_report
            dr = r.duizhang_report
            dist = r.tone_distribution

            writer.writerow([
                r.poem_title,
                r.poem_author,
                r.form,
                mr.style if mr else "",
                r.total_lines,
                r.total_chars,
                f"{mr.compliance_rate:.1f}%" if mr else "",
                mr.overall_judgment if mr else "",
                len(mr.violations) if mr else 0,
                ",".join(str(i) for i in mr.guping_lines) if mr and mr.guping_lines else "",
                ",".join(str(i) for i in mr.sanpingdiao_lines) if mr and mr.sanpingdiao_lines else "",
                ",".join(str(i) for i in mr.sanzewei_lines) if mr and mr.sanzewei_lines else "",
                rr.rhyme_yunbu if rr else "",
                rr.is_compliant if rr else "",
                rr.neighboring_rhyme if rr else "",
                dist.ping_count,
                dist.ze_count,
                dist.rusheng_count,
                dist.unknown_count,
                dr.overall_score if dr else 0,
                r.overall_score,
            ])

        return output.getvalue()

    # ─── 保存到文件 ───

    def save_report(
        self,
        result: ScansionResult,
        output_dir: str,
        filename: str = None,
        formats: List[str] = None,
    ) -> Dict[str, str]:
        """将分析报告保存到文件

        Args:
            result: 扫描结果
            output_dir: 输出目录
            filename: 文件名（不含扩展名，默认使用诗歌标题）
            formats: 输出格式列表 ["text", "json", "html", "csv"]

        Returns:
            Dict[str, str]: {format: file_path}
        """
        formats = formats or ["text", "json"]
        filename = filename or sanitize_filename(
            result.poem_title or f"poem_{result.total_lines}lines"
        )
        os.makedirs(output_dir, exist_ok=True)

        saved = {}
        for fmt in formats:
            if fmt == "text":
                content = self.generate_text_report(result)
                ext = ".txt"
            elif fmt == "json":
                content = self.generate_json_report(result)
                ext = ".json"
            elif fmt == "html":
                content = self.generate_html_report(result)
                ext = ".html"
            elif fmt == "csv":
                content = self.generate_csv_report([result])
                ext = ".csv"
            else:
                continue

            fp = os.path.join(output_dir, f"{filename}{ext}")
            with open(fp, "w", encoding="utf-8") as f:
                f.write(content)
            saved[fmt] = fp
            logger.info(f"已保存 {fmt} 报告: {fp}")

        return saved

    # ─── 批量保存 ───

    def save_batch_report(
        self,
        batch_result: BatchResult,
        output_dir: str,
        formats: List[str] = None,
    ) -> Dict[str, str]:
        """保存批量分析汇总报告"""
        formats = formats or ["text", "json", "csv"]
        os.makedirs(output_dir, exist_ok=True)
        saved = {}

        summary = batch_result.to_dict()

        for fmt in formats:
            if fmt == "json":
                fp = os.path.join(output_dir, "batch_summary.json")
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(summary, f, ensure_ascii=False, indent=2)
                saved[fmt] = fp

            elif fmt == "csv":
                fp = os.path.join(output_dir, "batch_summary.csv")
                if batch_result.results:
                    csv_content = self.generate_csv_report(batch_result.results)
                    with open(fp, "w", encoding="utf-8") as f:
                        f.write(csv_content)
                    saved[fmt] = fp

            elif fmt == "text":
                fp = os.path.join(output_dir, "batch_summary.txt")
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(self._batch_text_summary(batch_result))
                saved[fmt] = fp

        return saved

    def _batch_text_summary(self, batch_result: BatchResult) -> str:
        """生成批量分析文本摘要"""
        from collections import Counter
        lines = [
            "=" * 50,
            "批量分析汇总报告",
            "=" * 50,
            f"总诗歌数: {batch_result.total_poems}",
            f"成功: {batch_result.succeeded}",
            f"失败: {batch_result.failed}",
            f"成功率: {batch_result.success_rate:.1f}%",
            f"耗时: {batch_result.duration_seconds:.1f}秒",
            "",
        ]

        if batch_result.results:
            forms = Counter(r.form for r in batch_result.results if r.form)
            yunbus = Counter(
                r.rhyme_report.rhyme_yunbu
                for r in batch_result.results
                if r.rhyme_report and r.rhyme_report.rhyme_yunbu
            )
            scores = [r.overall_score for r in batch_result.results]
            avg = sum(scores) / max(1, len(scores))

            lines.append(f"平均评分: {avg:.1f}")
            lines.append("")
            lines.append("体裁分布:")
            for form, count in forms.most_common(10):
                lines.append(f"  {form}: {count}首")
            lines.append("")
            lines.append("韵部分布(Top 10):")
            for yb, count in yunbus.most_common(10):
                lines.append(f"  {yb}: {count}次")

        if batch_result.errors:
            lines.append("")
            lines.append("失败详情:")
            for err in batch_result.errors[:10]:
                lines.append(f"  {err.get('poem','?')}: {err.get('error','?')}")

        return "\n".join(lines)
