# -*- coding: utf-8 -*-
"""
将软著源代码汇总转换为 PDF 格式
"""
import os
import re

from fpdf import FPDF, XPos, YPos

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "软著_源代码汇总.txt")
OUTPUT_FILE = os.path.join(BASE_DIR, "软著_源代码正文.pdf")

SOFTWARE_NAME = "唐诗意象智能分析系统"


def extract_source_code_section(text):
    """提取源代码正文部分"""
    marker = "三、源代码正文"
    idx = text.find(marker)
    if idx == -1:
        raise ValueError("未找到源代码正文部分")
    return text[idx:]


def convert_to_pdf():
    if not os.path.exists(INPUT_FILE):
        print(f"未找到输入文件: {INPUT_FILE}")
        print("请先运行 generate_soft_copyright.py 生成源代码汇总文件。")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        all_text = f.read()

    code_section = extract_source_code_section(all_text)
    lines = code_section.split("\n")

    # 查找 Windows 中文字体
    font_candidates = [
        "C:/Windows/Fonts/simsun.ttc",      # 宋体
        "C:/Windows/Fonts/simfang.ttf",      # 仿宋
        "C:/Windows/Fonts/simhei.ttf",       # 黑体
        "C:/Windows/Fonts/msyh.ttc",         # 微软雅黑
    ]
    font_path = None
    for fp in font_candidates:
        if os.path.exists(fp):
            font_path = fp
            break

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── 标题 ──
    if font_path:
        pdf.add_font("CJK", "", font_path)
        pdf.set_font("CJK", "", 14)
    else:
        pdf.set_font("Courier", "", 14)

    pdf.cell(0, 10, SOFTWARE_NAME, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("CJK", "", 9) if font_path else pdf.set_font("Courier", "", 8)
    pdf.cell(0, 6, "— 源代码正文 —", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(4)

    # ── 源代码正文 ──
    line_count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("=" * 10) or stripped.startswith("三、源代码正文"):
            continue

        line_count += 1

        if font_path:
            pdf.set_font("CJK", "", 7.5)
        else:
            pdf.set_font("Courier", "", 7)

        out_line = line.rstrip()
        # 替换可能缺字的特殊字符
        out_line = (out_line.replace("\u2713", "V").replace("\u2717", "X")
                           .replace("\u2605", "*").replace("\u25c6", "*"))
        try:
            pdf.cell(0, 4.2, out_line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        except Exception:
            try:
                pdf.add_page()
                pdf.cell(0, 4.2, out_line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            except Exception as e:
                print(f"跳过无法写入的行: {str(e)[:50]}")

    pdf.output(OUTPUT_FILE)
    print(f"\nPDF 生成成功！")
    print(f"  输出文件: {OUTPUT_FILE}")
    print(f"  有效代码行: {line_count}")
    print(f"  文件大小: {os.path.getsize(OUTPUT_FILE) / 1024:.1f} KB")


if __name__ == "__main__":
    convert_to_pdf()
