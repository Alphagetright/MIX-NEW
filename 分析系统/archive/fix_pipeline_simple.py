#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix pipeline doc: remove section 18, add new screenshots, update rels."""
import os, shutil

BASE = 'C:/Users/Administrator/Desktop/新建文件夹 (14)/unpacked_pipe_new'
IMG_SRC = 'C:/Users/Administrator/Desktop/All Mix'

# ── Step 1: Copy new images to media ──
media = f'{BASE}/word/media'
for f in ['pipeline_cli_help.png', 'pipeline_run.png', 'pipeline_output.png',
          'p_login.png', 'p_register.png', 'p_dashboard.png', 'p_home.png', 'p_api_health.png']:
    shutil.copy2(f'{IMG_SRC}/{f}', f'{media}/{f}')
    print(f'Copied: {f}')

# ── Step 2: Update document.xml.rels ──
rels_path = f'{BASE}/word/_rels/document.xml.rels'
with open(rels_path, 'r', encoding='utf-8') as f:
    rels = f.read()

new_rels = {
    'rId14': 'media/pipeline_cli_help.png',
    'rId15': 'media/pipeline_run.png',
    'rId16': 'media/pipeline_output.png',
    'rId17': 'media/p_login.png',
    'rId18': 'media/p_register.png',
    'rId19': 'media/p_dashboard.png',
    'rId20': 'media/p_home.png',
    'rId21': 'media/p_api_health.png',
}

insert = ''
for rid, target in new_rels.items():
    insert += f'  <Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="{target}"/>\n'

rels = rels.replace('</Relationships>', insert + '</Relationships>')

with open(rels_path, 'w', encoding='utf-8') as f:
    f.write(rels)
print('Updated relationships')

# ── Step 3: Edit document.xml ──
doc_path = f'{BASE}/word/document.xml'
with open(doc_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find section boundaries in body
# Line numbers (1-based in the file, 0-based in list)
s18_h1_line = None  # "十八、CLI接口层"
s19_h1_line = None  # "十九、Web前端模块"
for i, line in enumerate(lines):
    if '十八、CLI接口层' in line:
        s18_h1_line = i
    elif '十九、Web前端模块' in line:
        s19_h1_line = i

print(f'Section 18 heading at line {s18_h1_line}, Section 19 at line {s19_h1_line}')

if s18_h1_line is None or s19_h1_line is None:
    print('ERROR: Could not find section boundaries')
    exit(1)

# Find the paragraph start for section 18 heading
# Walk backwards to find <w:p> that contains the heading
s18_start = s18_h1_line
while s18_start > 0 and '<w:p>' not in lines[s18_start] and '<w:p ' not in lines[s18_start]:
    s18_start -= 1
# Also include the page break BEFORE section 18
s18_start -= 1
while s18_start > 0 and '<w:p>' not in lines[s18_start] and '<w:p ' not in lines[s18_start]:
    s18_start -= 1

# s18_end = the page break/empty paragraph before section 19
s18_end = s19_h1_line
# Walk back to find </w:p> before section 19 heading
# Include the page break before section 19
s18_end -= 1  # start from line before 十九 heading
while s18_end > s18_start and '</w:p>' not in lines[s18_end]:
    s18_end -= 1
s18_end += 1  # include the </w:p> line

print(f'Removing lines {s18_start} to {s18_end-1} ({s18_end - s18_start} lines)')
print(f'  First: {lines[s18_start].strip()[:60]}')
print(f'  Last:  {lines[s18_end-1].strip()[:60]}')

# Remove section 18
new_lines = lines[:s18_start] + lines[s18_end:]

# Find new section 19 position
s19_new = None
for i, line in enumerate(new_lines):
    if '十九、Web前端模块' in line:
        s19_new = i
        break

print(f'New section 19 at line {s19_new}')

# ── Step 4: Generate new section 18 XML ──
ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"'

# Use the same namespace prefix as the doc
W = 'w'
R = 'r'

def make_img_xml(rid, docpr_id, fname, cx=5029200, cy=3143250):
    return f'''    <{W}:p>
      <{W}:pPr><{W}:jc w:val="center"/></{W}:pPr>
      <{W}:r>
        <{W}:drawing>
          <wp:inline distT="0" distB="0" distL="0" distR="0" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
            <wp:extent cx="{cx}" cy="{cy}"/>
            <wp:effectExtent l="0" t="0" r="0" b="0"/>
            <wp:docPr id="{docpr_id}" name="{fname}"/>
            <wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>
            <a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
              <pic:pic>
                <pic:nvPicPr><pic:cNvPr id="0" name="{fname}"/><pic:cNvPicPr/></pic:nvPicPr>
                <pic:blipFill><a:blip {R}:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
                <pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
              </pic:pic>
            </a:graphicData></a:graphic>
          </wp:inline>
        </{W}:drawing>
      </{W}:r>
    </{W}:p>'''

sect18_xml = f'''
    <{W}:p>
      <{W}:pPr><{W}:pStyle w:val="Heading1"/><{W}:rPr>
        <{W}:rFonts w:ascii="黑体" w:hAnsi="黑体" w:eastAsia="黑体"/>
        <{W}:b/><{W}:sz w:val="28"/><{W}:szCs w:val="28"/>
      </{W}:rPr></{W}:pPr>
      <{W}:r><{W}:rPr>
        <{W}:rFonts w:ascii="黑体" w:hAnsi="黑体" w:eastAsia="黑体"/>
        <{W}:b/><{W}:sz w:val="28"/><{W}:szCs w:val="28"/>
      </{W}:rPr><{W}:t xml:space="preserve">十八、系统运行截图</{W}:t></{W}:r>
    </{W}:p>

    <{W}:p>
      <{W}:pPr><{W}:pStyle w:val="Heading2"/></{W}:pPr>
      <{W}:r><{W}:rPr>
        <{W}:rFonts w:ascii="黑体" w:hAnsi="黑体" w:eastAsia="黑体"/>
        <{W}:b/><{W}:sz w:val="24"/><{W}:szCs w:val="24"/>
      </{W}:rPr><{W}:t xml:space="preserve">18.1 管线CLI命令帮助</{W}:t></{W}:r>
    </{W}:p>
    <{W}:p>
      <{W}:pPr><{W}:ind w:firstLine="420"/></{W}:pPr>
      <{W}:r><{W}:rPr>
        <{W}:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体"/>
        <{W}:sz w:val="21"/><{W}:szCs w:val="21"/>
      </{W}:rPr><{W}:t xml:space="preserve">系统提供完整的CLI命令接口，支持run（执行标注管线）、validate（校验数据）、report（生成报告）、clean（清理缓存）、config（管理配置）、stats（运行统计）七个子命令。通过python demo.py --help可查看所有命令及参数说明。</{W}:t></{W}:r>
    </{W}:p>
    <{W}:p>
      <{W}:pPr><{W}:jc w:val="center"/></{W}:pPr>
      <{W}:r><{W}:rPr>
        <{W}:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体"/>
        <{W}:b/><{W}:color w:val="2C3E50"/><{W}:sz w:val="24"/><{W}:szCs w:val="24"/>
      </{W}:rPr><{W}:t xml:space="preserve">图1： 管线CLI命令帮助</{W}:t></{W}:r>
    </{W}:p>
{make_img_xml('rId14', 14, 'pipeline_cli_help.png')}

    <{W}:p>
      <{W}:pPr><{W}:pStyle w:val="Heading2"/></{W}:pPr>
      <{W}:r><{W}:rPr>
        <{W}:rFonts w:ascii="黑体" w:hAnsi="黑体" w:eastAsia="黑体"/>
        <{W}:b/><{W}:sz w:val="24"/><{W}:szCs w:val="24"/>
      </{W}:rPr><{W}:t xml:space="preserve">18.2 管线运行过程</{W}:t></{W}:r>
    </{W}:p>
    <{W}:p>
      <{W}:pPr><{W}:ind w:firstLine="420"/></{W}:pPr>
      <{W}:r><{W}:rPr>
        <{W}:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体"/>
        <{W}:sz w:val="21"/><{W}:szCs w:val="21"/>
      </{W}:rPr><{W}:t xml:space="preserve">执行run命令启动标注管线，系统按"输入读取→文本预处理→AI标注引擎→结果解析与校验→数据输出"五步流程自动处理。输入支持TXT/JSON/CSV/MD格式，AI引擎完成结构化标注后经过多层校验确保数据质量，最终输出标准格式的标注结果。</{W}:t></{W}:r>
    </{W}:p>
    <{W}:p>
      <{W}:pPr><{W}:jc w:val="center"/></{W}:pPr>
      <{W}:r><{W}:rPr>
        <{W}:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体"/>
        <{W}:b/><{W}:color w:val="2C3E50"/><{W}:sz w:val="24"/><{W}:szCs w:val="24"/>
      </{W}:rPr><{W}:t xml:space="preserve">图2： 管线运行过程</{W}:t></{W}:r>
    </{W}:p>
{make_img_xml('rId15', 15, 'pipeline_run.png')}

    <{W}:p>
      <{W}:pPr><{W}:pStyle w:val="Heading2"/></{W}:pPr>
      <{W}:r><{W}:rPr>
        <{W}:rFonts w:ascii="黑体" w:hAnsi="黑体" w:eastAsia="黑体"/>
        <{W}:b/><{W}:sz w:val="24"/><{W}:szCs w:val="24"/>
      </{W}:rPr><{W}:t xml:space="preserve">18.3 标注数据输出</{W}:t></{W}:r>
    </{W}:p>
    <{W}:p>
      <{W}:pPr><{W}:ind w:firstLine="420"/></{W}:pPr>
      <{W}:r><{W}:rPr>
        <{W}:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体"/>
        <{W}:sz w:val="21"/><{W}:szCs w:val="21"/>
      </{W}:rPr><{W}:t xml:space="preserve">管线输出结构化JSON格式的标注数据，包含运行元信息、诗歌原文、多维标注结果（意象分析/情感分析/结构分析）及质量评分。支持JSON/CSV/XML三种导出格式。</{W}:t></{W}:r>
    </{W}:p>
    <{W}:p>
      <{W}:pPr><{W}:jc w:val="center"/></{W}:pPr>
      <{W}:r><{W}:rPr>
        <{W}:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体"/>
        <{W}:b/><{W}:color w:val="2C3E50"/><{W}:sz w:val="24"/><{W}:szCs w:val="24"/>
      </{W}:rPr><{W}:t xml:space="preserve">图3： 标注数据输出</{W}:t></{W}:r>
    </{W}:p>
{make_img_xml('rId16', 16, 'pipeline_output.png')}

    <{W}:p>
      <{W}:r><{W}:br w:type="page"/></{W}:r>
    </{W}:p>
'''

# Insert new content before section 19 heading
insert_before = s19_new
new_lines = new_lines[:insert_before] + [sect18_xml] + new_lines[insert_before:]

with open(doc_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print(f'Inserted new section 18 at line {insert_before}')

# ── Step 5: Verify ──
with open(doc_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Check no stale section 18 body
import re
body_s18 = [m.start() for m in re.finditer('十八、CLI接口层', content)]
print(f'Occurrences of 十八、CLI接口层: {len(body_s18)}' + (f' at {body_s18}' if body_s18 else ''))

# Check new section exists
if '十八、系统运行截图' in content:
    print('New section 18 present: OK')

print('Done!')
