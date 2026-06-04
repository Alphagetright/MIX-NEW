# -*- coding: utf-8 -*-
"""
古典诗词音韵格律分析引擎 — 韵脚分析器
========================================
提取诗歌韵脚、查询韵部归属、检测邻韵通押，
支持近体诗（绝句/律诗）押韵规则。
"""
from typing import Any, Dict, List, Optional, Set, Tuple

from .errors import RhymeError, safe_call
from .logger import get_logger, LoggerMixin
from .models import RhymeChar, RhymeReport
from .pingshui_db import PingShuiYunDB

logger = get_logger("rhyme_analyzer")


class RhymeAnalyzer(LoggerMixin):
    """韵脚分析器"""

    def __init__(self, db: PingShuiYunDB):
        self._db = db

    # ─── 韵脚提取 ───

    def extract_rhyme_chars(
        self, poem_lines: List[str], form: str = None
    ) -> List[RhymeChar]:
        """提取韵脚字

        规则：
        - 绝句（4句）：2、4句末字必须押韵
        - 律诗（8句）：2、4、6、8句末字必须押韵
        - 若第一句末字为平声，则首句入韵
        """
        if not poem_lines:
            return []

        n_lines = len(poem_lines)
        rhyme_positions = []

        # 偶数句必须押韵
        for i in range(1, n_lines, 2):
            rhyme_positions.append(i)

        # 首句入韵判断
        first_last = poem_lines[0][-1] if poem_lines[0] else ""
        if first_last and self._db.get_tone(first_last) == "平":
            rhyme_positions.insert(0, 0)

        # 对长诗（排律），每隔一句押韵
        if n_lines > 8:
            rhyme_positions = list(range(1, n_lines, 2))

        rhyme_chars = []
        for line_idx in rhyme_positions:
            if line_idx >= len(poem_lines):
                continue
            line = poem_lines[line_idx]
            if not line:
                continue
            last_char = line[-1]
            yunbu = self._db.get_yunbu(last_char)
            yunbu_category = self._db.get_yunbu_category(yunbu) if yunbu else "未知"

            char = RhymeChar(
                char=last_char,
                line_number=line_idx + 1,
                position=len(line),
                yunbu=yunbu or "",
                yunbu_category=yunbu_category,
                is_rhyme_required=(line_idx % 2 == 1),  # 偶数句必须押韵
            )
            rhyme_chars.append(char)

        return rhyme_chars

    # ─── 韵部统计 ───

    def _get_yunbu_frequency(
        self, rhyme_chars: List[RhymeChar]
    ) -> List[Tuple[str, int]]:
        """统计各韵部出现频率"""
        freq = {}
        for rc in rhyme_chars:
            if rc.yunbu:
                freq[rc.yunbu] = freq.get(rc.yunbu, 0) + 1
        return sorted(freq.items(), key=lambda x: -x[1])

    # ─── 主分析 ───

    def analyze_rhyme_scheme(
        self, poem_lines: List[str], form: str = None
    ) -> RhymeReport:
        """分析押韵模式"""
        if not poem_lines:
            return RhymeReport()

        rhyme_chars = self.extract_rhyme_chars(poem_lines, form)

        # 统计韵部频率
        yunbu_freq = self._get_yunbu_frequency(rhyme_chars)
        main_yunbu = yunbu_freq[0][0] if yunbu_freq else ""

        # 合规检查
        is_compliant = True
        violations = []
        unique_yunbus = set()
        for rc in rhyme_chars:
            if rc.yunbu:
                unique_yunbus.add(rc.yunbu)

        # 检查是否所有必押韵脚同韵部
        required_chars = [rc for rc in rhyme_chars if rc.is_rhyme_required]
        required_yunbus = set(rc.yunbu for rc in required_chars if rc.yunbu)
        first_char_optional = rhyme_chars[0] if rhyme_chars and not rhyme_chars[0].is_rhyme_required else None

        if len(required_yunbus) > 1:
            is_compliant = False
            for rc in required_chars:
                if rc.yunbu and rc.yunbu != main_yunbu:
                    violations.append(
                        f"第{rc.line_number}句「{rc.char}」属{rc.yunbu}韵，"
                        f"与主押韵{main_yunbu}不押"
                    )

        # 检查首句是否邻韵通押（"孤雁出群格"）
        neighboring_rhyme = False
        if first_char_optional and first_char_optional.yunbu and main_yunbu:
            if first_char_optional.yunbu != main_yunbu:
                if self._db.is_neighboring(first_char_optional.yunbu, main_yunbu):
                    neighboring_rhyme = True
                    violations.append(
                        f"首句邻韵通押：{first_char_optional.char}属"
                        f"{first_char_optional.yunbu}韵（邻韵{main_yunbu}）"
                    )
                else:
                    is_compliant = False
                    violations.append(
                        f"首句出韵：{first_char_optional.char}属"
                        f"{first_char_optional.yunbu}韵，不与{main_yunbu}通押"
                    )

        # 如果只有一个韵部，但和必押韵脚韵部不同，也算邻韵
        if not is_compliant and len(unique_yunbus) == 2 and main_yunbu:
            other_yunbu = [y for y in unique_yunbus if y != main_yunbu][0]
            if self._db.is_neighboring(main_yunbu, other_yunbu):
                neighboring_rhyme = True
                is_compliant = True
                violations = []

        # 韵脚密度
        total_chars = sum(len(l) for l in poem_lines)
        rhyme_count = len(rhyme_chars)
        density = rhyme_count / max(1, total_chars)

        # 去重韵脚
        unique_rhyme_count = len(set(rc.char for rc in rhyme_chars))

        # 生成韵部描述
        yunbu_desc = (
            self._describe_yunbu(main_yunbu, rhyme_chars)
            if main_yunbu
            else "未识别"
        )

        return RhymeReport(
            poem_title="",
            form=form or "",
            rhyme_chars=rhyme_chars,
            rhyme_yunbu=main_yunbu,
            yunbu_description=yunbu_desc,
            is_compliant=is_compliant,
            neighboring_rhyme=neighboring_rhyme,
            violations=violations,
            rhyme_density=density,
            unique_rhyme_count=unique_rhyme_count,
        )

    # ─── 工具 ───

    def _describe_yunbu(
        self, main_yunbu: str, rhyme_chars: List[RhymeChar]
    ) -> str:
        """生成韵部可读描述"""
        category = self._db.get_yunbu_category(main_yunbu)
        # 查找韵部序号
        all_yunbu = self._db.get_all_yunbu_names()
        if main_yunbu in all_yunbu:
            idx = all_yunbu.index(main_yunbu) + 1
        else:
            idx = 0

        chars_in_yunbu = [rc.char for rc in rhyme_chars if rc.yunbu == main_yunbu]
        return f"{category}声·{main_yunbu}韵（{', '.join(chars_in_yunbu)}）"

    def get_rhyme_density(
        self, poem_lines: List[str], form: str = None
    ) -> float:
        """韵脚密度分析"""
        chars = self.extract_rhyme_chars(poem_lines, form)
        total = sum(len(l) for l in poem_lines)
        return len(chars) / max(1, total)
