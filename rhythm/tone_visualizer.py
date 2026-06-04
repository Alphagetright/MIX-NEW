# -*- coding: utf-8 -*-
"""
古典诗词音韵格律分析引擎 — 声调模式可视化
============================================
支持纯文本和HTML格式的声调可视化输出，
生成平仄标记串、声调分布图、ECharts配置。
"""
from typing import Any, Dict, List, Optional, Tuple

from .logger import get_logger
from .models import (
    MeterViolation,
    PingzeAnnotation,
    ScansionResult,
    ToneDistribution,
)

logger = get_logger("tone_visualizer")


class ToneVisualizer:
    """声调可视化器"""

    # ─── 纯文本可视化 ───

    def to_text(self, result: ScansionResult) -> str:
        """生成纯文本可视化报告"""
        lines = []

        # 标题
        header = f"《{result.poem_title}》{result.poem_author}" if result.poem_author else result.poem_title
        form_info = f"  [{result.form}]" if result.form else ""
        lines.append(f"{header}{form_info}")
        lines.append("")

        # 诗句 + 平仄标记
        for i, line_ann in enumerate(result.pingze_annotations):
            line_text = "".join(a.char for a in line_ann)
            pz_symbols = "".join(a.tone_symbol for a in line_ann)
            pz_labels = "/".join(a.tone for a in line_ann)

            # 标记韵脚行
            rhyme_mark = ""
            if result.rhyme_report:
                for rc in result.rhyme_report.rhyme_chars:
                    if rc.line_number == i + 1:
                        rhyme_mark = " ★韵"
                        break

            lines.append(f"{line_text}  {pz_symbols}  ({pz_labels}){rhyme_mark}")

        lines.append("")

        # 声调分布
        dist = result.tone_distribution
        lines.append(f"声调分布: 平声{dist.ping_count} 仄声{dist.ze_count} 入声{dist.rusheng_count} 未知{dist.unknown_count}")

        # 格律检查
        if result.meter_report:
            mr = result.meter_report
            lines.append(f"格律: {mr.overall_judgment} (合规率{mr.compliance_rate:.1f}%)")
            if mr.guping_lines:
                lines.append("[孤平] 第" + ",".join(str(i) for i in mr.guping_lines) + "句")
            if mr.sanpingdiao_lines:
                lines.append("[三平调] 第" + ",".join(str(i) for i in mr.sanpingdiao_lines) + "句")
            if mr.sanzewei_lines:
                lines.append("[三仄尾] 第" + ",".join(str(i) for i in mr.sanzewei_lines) + "句")
            for v in mr.violations:
                lines.append(f"  · {v.description}")

        # 韵脚分析
        if result.rhyme_report:
            rr = result.rhyme_report
            if rr.rhyme_yunbu:
                lines.append(f"韵脚: {', '.join(rc.char for rc in rr.rhyme_chars)} => {rr.yunbu_description}")
            if rr.is_compliant:
                lines.append("押韵: 合韵 [OK]")
            else:
                lines.append("押韵: 出韵 [NO]")
                for v in rr.violations:
                    lines.append(f"  · {v}")
            if rr.neighboring_rhyme:
                lines.append("邻韵通押 (邻韵)")

        # 对仗检测
        if result.duizhang_report:
            dr = result.duizhang_report
            if dr.couplets:
                for c in dr.couplets:
                    if c.is_duizhang:
                        lines.append(f"对仗 ({c.couplet_name}): [OK] {c.duizhang_type} ({c.score:.0f}/100)")
                    else:
                        lines.append(f"对仗 ({c.couplet_name}): [NO] 非对仗")
            if dr.overall_score > 0:
                lines.append(f"对仗综合评分: {dr.overall_score:.1f}/100")

        # 综合评分
        lines.append(f"\n综合评分: {result.overall_score:.0f}/100")
        lines.append(f"总结: {result.summary}")

        return "\n".join(lines)

    # ─── HTML 可视化 ───

    def to_html(self, result: ScansionResult) -> str:
        """生成独立HTML页面"""
        lines_html = self._build_lines_html(result)
        dist_html = self._build_distribution_html(result.tone_distribution)
        meter_html = self._build_meter_html(result)
        rhyme_html = self._build_rhyme_html(result)
        duizhang_html = self._build_duizhang_html(result)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>音韵格律分析 — {result.poem_title}</title>
<style>
body {{ font-family: "SimSun", "Songti SC", serif; max-width: 800px; margin: 40px auto; padding: 0 20px; background: #faf8f5; color: #2c2c2c; }}
h1 {{ text-align: center; font-size: 24px; border-bottom: 2px solid #8b0000; padding-bottom: 10px; }}
.info {{ text-align: center; color: #666; margin-bottom: 20px; }}
.poem {{ background: #fff; padding: 20px 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.line {{ font-size: 20px; margin: 8px 0; display: flex; align-items: center; }}
.char {{ padding: 2px; }}
.ping {{ color: #0066cc; }} .ze {{ color: #cc0000; }} .rusheng {{ color: #9933cc; }} .unknown {{ color: #999; }}
.pz-str {{ font-size: 14px; color: #888; margin-left: 15px; letter-spacing: 2px; }}
.rhyme-mark {{ color: #cc6600; font-weight: bold; }}
.section {{ background: #fff; margin-top: 16px; padding: 15px 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.section h2 {{ font-size: 18px; border-left: 3px solid #8b0000; padding-left: 10px; margin: 0 0 10px 0; }}
.bar {{ display: inline-block; height: 20px; margin-right: 2px; border-radius: 3px; }}
.violation {{ color: #cc0000; }}
.ok {{ color: #006600; }}
.score {{ font-size: 28px; text-align: center; margin: 20px 0; }}
.footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; }}
</style>
</head>
<body>
<h1>《{result.poem_title}》{result.poem_author}</h1>
<div class="info">{result.form} | {result.total_lines}句{result.total_chars}字 | 综合评分 {result.overall_score:.0f}/100</div>

<div class="poem">
{lines_html}
</div>

<div class="section">
<h2>声调分布</h2>
{dist_html}
</div>

{meter_html}
{rhyme_html}
{duizhang_html}

<div class="score">
综合评分: <strong>{result.overall_score:.0f}/100</strong><br>
<span style="font-size:14px;color:#666;">{result.summary}</span>
</div>

<div class="footer">由 古典诗词音韵格律自动分析引擎 生成</div>
</body>
</html>"""

    # ─── HTML 辅助 ───

    def _build_lines_html(self, result: ScansionResult) -> str:
        lines = []
        for i, line_ann in enumerate(result.pingze_annotations):
            chars_html = []
            for a in line_ann:
                cls = {"平": "ping", "仄": "ze", "仄(入)": "rusheng", "未知": "unknown"}.get(a.tone, "unknown")
                chars_html.append(f'<span class="char {cls}" title="{a.yunbu}">{a.char}</span>')

            pz_symbols = "".join(a.tone_symbol for a in line_ann)

            rhyme_mark = ""
            if result.rhyme_report:
                for rc in result.rhyme_report.rhyme_chars:
                    if rc.line_number == i + 1:
                        rhyme_mark = ' <span class="rhyme-mark">(韵)</span>'
                        break

            lines.append(
                f'<div class="line">{"".join(chars_html)} '
                f'<span class="pz-str">{pz_symbols}</span>{rhyme_mark}</div>'
            )
        return "\n".join(lines)

    def _build_distribution_html(self, dist: ToneDistribution) -> str:
        total = max(1, dist.total_chars)
        d = dist.to_dict()
        return (
            f'<p>平声: {dist.ping_count} | 仄声: {dist.ze_count} | '
            f'入声: {dist.rusheng_count} | 未知: {dist.unknown_count}</p>'
            f'<div>'
            f'<span class="bar" style="width:{dist.ping_count/total*200}px;background:#0066cc;"></span> '
            f'平声 {d["平声占比"]}%<br>'
            f'<span class="bar" style="width:{dist.ze_count/total*200}px;background:#cc0000;"></span> '
            f'仄声 {d["仄声占比"]}%<br>'
            f'<span class="bar" style="width:{dist.rusheng_count/total*200}px;background:#9933cc;"></span> '
            f'入声 {d["入声占比"]}%'
            f'</div>'
        )

    def _build_meter_html(self, result: ScansionResult) -> str:
        mr = result.meter_report
        if not mr:
            return ""
        parts = [f'<div class="section"><h2>格律检查</h2>']
        parts.append(f'<p>判定: <strong>{mr.overall_judgment}</strong> | 合规率: {mr.compliance_rate:.1f}%</p>')
        if mr.guping_lines:
            parts.append(f'<p class="violation">孤平: 第{",".join(str(i) for i in mr.guping_lines)}句</p>')
        if mr.sanpingdiao_lines:
            parts.append(f'<p class="violation">三平调: 第{",".join(str(i) for i in mr.sanpingdiao_lines)}句</p>')
        if mr.sanzewei_lines:
            parts.append(f'<p class="violation">三仄尾: 第{",".join(str(i) for i in mr.sanzewei_lines)}句</p>')
        for v in mr.violations:
            parts.append(f'<p class="violation">· {v.description}</p>')
        parts.append('</div>')
        return "\n".join(parts)

    def _build_rhyme_html(self, result: ScansionResult) -> str:
        rr = result.rhyme_report
        if not rr:
            return ""
        parts = [f'<div class="section"><h2>韵脚分析</h2>']
        if rr.rhyme_yunbu:
            parts.append(f'<p>韵部: {rr.yunbu_description}</p>')
        parts.append(f'<p>押韵: {"合韵 ✓" if rr.is_compliant else "出韵 ✗"}')
        if rr.neighboring_rhyme:
            parts.append(' | 邻韵通押')
        parts.append('</p>')
        for v in rr.violations:
            parts.append(f'<p class="violation">· {v}</p>')
        parts.append('</div>')
        return "\n".join(parts)

    def _build_duizhang_html(self, result: ScansionResult) -> str:
        dr = result.duizhang_report
        if not dr or not dr.couplets:
            return ""
        parts = [f'<div class="section"><h2>对仗检测</h2>']
        for c in dr.couplets:
            icon = "✓" if c.is_duizhang else "✗"
            cls = "ok" if c.is_duizhang else "violation"
            parts.append(
                f'<p class="{cls}">{icon} {c.couplet_name}: {c.duizhang_type} ({c.score:.0f}/100)</p>'
            )
        if dr.overall_score > 0:
            parts.append(f'<p>对仗综合评分: {dr.overall_score:.1f}/100</p>')
        parts.append('</div>')
        return "\n".join(parts)

    # ─── ECharts 配置 ───

    def to_echarts_option(self, result: ScansionResult) -> Dict[str, Any]:
        """生成ECharts配置（用于Web展示）"""
        dist = result.tone_distribution.to_dict()
        return {
            "title": {"text": f"{result.poem_title} — 声调分布"},
            "tooltip": {"trigger": "item"},
            "series": [
                {
                    "name": "声调",
                    "type": "pie",
                    "radius": "50%",
                    "data": [
                        {"value": dist["平声"], "name": "平声", "itemStyle": {"color": "#0066cc"}},
                        {"value": dist["仄声"], "name": "仄声", "itemStyle": {"color": "#cc0000"}},
                        {"value": dist["入声"], "name": "入声", "itemStyle": {"color": "#9933cc"}},
                        {"value": dist["未知"], "name": "未知", "itemStyle": {"color": "#cccccc"}},
                    ],
                    "label": {"formatter": "{b}: {c} ({d}%)"},
                }
            ],
        }

    def generate_pingze_curve(self, annotations: List[List[PingzeAnnotation]]) -> List[int]:
        """平仄起伏曲线（平=1, 仄=-1, 入=-1, 未知=0）"""
        curve = []
        for line_ann in annotations:
            for ann in line_ann:
                if ann.tone == "平":
                    curve.append(1)
                elif ann.tone in ("仄", "仄(入)"):
                    curve.append(-1)
                else:
                    curve.append(0)
        return curve

    def generate_tone_heatmap(self, result: ScansionResult) -> Dict[str, Any]:
        """生成声调热力图数据"""
        rows = []
        for i, line_ann in enumerate(result.pingze_annotations):
            for j, ann in enumerate(line_ann):
                val = {"平": 1, "仄": -1, "仄(入)": -2, "未知": 0}.get(ann.tone, 0)
                rows.append([i + 1, j + 1, val])
        return {
            "rows": rows,
            "maxLines": result.total_lines,
            "maxChars": max(len(ann) for ann in result.pingze_annotations) if result.pingze_annotations else 0,
        }
