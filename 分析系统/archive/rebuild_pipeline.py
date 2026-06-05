#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rebuild pipeline document properly:
1. Remove section 十八 (CLI interface) from body
2. Copy new screenshots to media/
3. Update section 十九 with real web screenshots
4. Add pipeline running screenshot section
5. Clean up TOC stale entries
"""
import os, shutil, re, copy
from lxml import etree

BASE = 'C:/Users/Administrator/Desktop/新建文件夹 (14)/unpacked_pipe_fresh'
DOCX_PATH = 'C:/Users/Administrator/Desktop/新建文件夹 (14)/软著_古典诗歌文本结构化标注生产系统_软件说明书.docx'
IMG_SRC = 'C:/Users/Administrator/Desktop/All Mix'

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
WP = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
PIC = 'http://schemas.openxmlformats.org/drawingml/2006/picture'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'

NSMAP = {'w': W, 'r': R, 'wp': WP, 'a': A, 'pic': PIC}

# ─── Step 1: Copy new images to media ───
media_dir = f'{BASE}/word/media'
new_images = {
    'p_login.png': 'rId14',
    'p_register.png': 'rId15',
    'p_dashboard.png': 'rId16',
    'p_home.png': 'rId17',
    'p_api_health.png': 'rId18',
}

for img_name in new_images:
    src = f'{IMG_SRC}/{img_name}'
    dst = f'{media_dir}/{img_name}'
    shutil.copy2(src, dst)
    print(f'Copied {img_name}')

# ─── Step 2: Add image relationships ───
rels_file = f'{BASE}/word/_rels/document.xml.rels'
rels_tree = etree.parse(rels_file)
rels_root = rels_tree.getroot()

for img_name, rid in new_images.items():
    rel = etree.SubElement(rels_root, f'{{{REL}}}Relationship')
    rel.set('Id', rid)
    rel.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image')
    rel.set('Target', f'media/{img_name}')

rels_tree.write(rels_file, xml_declaration=True, encoding='UTF-8', pretty_print=False)
print('Added relationships')

# ─── Step 3: Parse document.xml ───
doc_file = f'{BASE}/word/document.xml'
parser = etree.XMLParser(remove_blank_text=False)
tree = etree.parse(doc_file, parser)
root = tree.getroot()
body = root.find(f'{{{W}}}body')

# Helper functions
def make_text_para(text, **props):
    """Create a paragraph with text."""
    p = etree.SubElement(body, f'{{{W}}}p')
    pPr = etree.SubElement(p, f'{{{W}}}pPr')
    rPr1 = etree.SubElement(pPr, f'{{{W}}}rPr')

    font = props.get('font', '宋体')
    size = props.get('size', 21)
    bold = props.get('bold', False)
    color = props.get('color', None)
    align = props.get('align', None)
    indent = props.get('indent', None)
    heading = props.get('heading', None)

    etree.SubElement(rPr1, f'{{{W}}}rFonts').set(f'{{{W}}}ascii', font)
    etree.SubElement(rPr1, f'{{{W}}}rFonts').set(f'{{{W}}}hAnsi', font)
    etree.SubElement(rPr1, f'{{{W}}}rFonts').set(f'{{{W}}}eastAsia', font)
    if bold:
        etree.SubElement(rPr1, f'{{{W}}}b')
    etree.SubElement(rPr1, f'{{{W}}}sz').set(f'{{{W}}}val', str(size))
    etree.SubElement(rPr1, f'{{{W}}}szCs').set(f'{{{W}}}val', str(size))

    if heading:
        etree.SubElement(pPr, f'{{{W}}}pStyle').set(f'{{{W}}}val', heading)
    if align:
        etree.SubElement(pPr, f'{{{W}}}jc').set(f'{{{W}}}val', align)
    if indent:
        ind = etree.SubElement(pPr, f'{{{W}}}ind')
        ind.set(f'{{{W}}}firstLine', str(indent))

    r = etree.SubElement(p, f'{{{W}}}r')
    rPr2 = etree.SubElement(r, f'{{{W}}}rPr')
    etree.SubElement(rPr2, f'{{{W}}}rFonts').set(f'{{{W}}}ascii', font)
    etree.SubElement(rPr2, f'{{{W}}}rFonts').set(f'{{{W}}}hAnsi', font)
    etree.SubElement(rPr2, f'{{{W}}}rFonts').set(f'{{{W}}}eastAsia', font)
    if bold:
        etree.SubElement(rPr2, f'{{{W}}}b')
    if color:
        etree.SubElement(rPr2, f'{{{W}}}color').set(f'{{{W}}}val', color)
    etree.SubElement(rPr2, f'{{{W}}}sz').set(f'{{{W}}}val', str(size))
    etree.SubElement(rPr2, f'{{{W}}}szCs').set(f'{{{W}}}val', str(size))

    t = etree.SubElement(r, f'{{{W}}}t')
    t.text = text
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    return p

def make_image_para(rid, docpr_id, filename, cx=5029200, cy=3143250):
    """Create a paragraph with an image."""
    p = etree.SubElement(body, f'{{{W}}}p')
    pPr = etree.SubElement(p, f'{{{W}}}pPr')
    etree.SubElement(pPr, f'{{{W}}}jc').set(f'{{{W}}}val', 'center')

    r = etree.SubElement(p, f'{{{W}}}r')
    drawing = etree.SubElement(r, f'{{{W}}}drawing')

    inline = etree.SubElement(drawing, f'{{{WP}}}inline')
    inline.set('distT', '0')
    inline.set('distB', '0')
    inline.set('distL', '0')
    inline.set('distR', '0')

    etree.SubElement(inline, f'{{{WP}}}extent').set('cx', str(cx)).set('cy', str(cy))
    eff = etree.SubElement(inline, f'{{{WP}}}effectExtent')
    eff.set('l', '0').set('t', '0').set('r', '0').set('b', '0')

    dp = etree.SubElement(inline, f'{{{WP}}}docPr')
    dp.set('id', str(docpr_id)).set('name', filename)

    cnf = etree.SubElement(inline, f'{{{WP}}}cNvGraphicFramePr')
    etree.SubElement(cnf, f'{{{A}}}graphicFrameLocks').set('noChangeAspect', '1')

    graphic = etree.SubElement(inline, f'{{{A}}}graphic')
    gd = etree.SubElement(graphic, f'{{{A}}}graphicData')
    gd.set('uri', 'http://schemas.openxmlformats.org/drawingml/2006/picture')

    pic = etree.SubElement(gd, f'{{{PIC}}}pic')

    nvp = etree.SubElement(pic, f'{{{PIC}}}nvPicPr')
    etree.SubElement(nvp, f'{{{PIC}}}cNvPr').set('id', '0').set('name', filename)
    etree.SubElement(nvp, f'{{{PIC}}}cNvPicPr')

    bf = etree.SubElement(pic, f'{{{PIC}}}blipFill')
    blip = etree.SubElement(bf, f'{{{A}}}blip')
    blip.set(f'{{{R}}}embed', rid)
    etree.SubElement(bf, f'{{{A}}}stretch').append(etree.SubElement(etree.SubElement(bf, f'{{{A}}}stretch'), f'{{{A}}}fillRect'))

    sppr = etree.SubElement(pic, f'{{{PIC}}}spPr')
    xfrm = etree.SubElement(sppr, f'{{{A}}}xfrm')
    etree.SubElement(xfrm, f'{{{A}}}off').set('x', '0').set('y', '0')
    etree.SubElement(xfrm, f'{{{A}}}ext').set('cx', str(cx)).set('cy', str(cy))
    geom = etree.SubElement(sppr, f'{{{A}}}prstGeom')
    geom.set('prst', 'rect')
    etree.SubElement(geom, f'{{{A}}}avLst')

    return p

# ─── Step 3a: Remove section 十八 (CLI) from body ───
children = list(body)
sect18_start = None
sect19_start = None
sect20_start = None

for i, child in enumerate(children):
    if child.tag == f'{{{W}}}p':
        texts = child.findall(f'.//{{{W}}}t')
        text = ''.join(t.text or '' for t in texts)
        if '十八、CLI接口层' in text:
            sect18_start = i
        elif '十九、Web前端模块' in text:
            sect19_start = i
        elif '二十、文件清单' in text:
            sect20_start = i

print(f'Body sections: 18={sect18_start}, 19={sect19_start}, 20={sect20_start}')

# Remove section 18 elements (from sect18_start to sect19_start-1)
if sect18_start is not None and sect19_start is not None:
    for i in range(sect19_start - 1, sect18_start - 1, -1):
        body.remove(children[i])
    print(f'Removed section 18 ({sect19_start - sect18_start} elements)')

# ─── Step 3b: Re-find section 19 and 20 positions after removal ───
children = list(body)
sect19_new = None
sect20_new = None
for i, child in enumerate(children):
    if child.tag == f'{{{W}}}p':
        texts = child.findall(f'.//{{{W}}}t')
        text = ''.join(t.text or '' for t in texts)
        if '十九、Web前端模块' in text:
            sect19_new = i
        elif '二十、文件清单' in text:
            sect20_new = i

print(f'After removal: 19={sect19_new}, 20={sect20_new}')

# ─── Step 3c: Add pipeline running screenshots section BEFORE section 19 ───
# Store elements to insert
new_elems_18 = []

# We'll build them as XML strings first, then parse
h1_xml = '''<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:pPr><w:pStyle w:val="Heading1"/><w:rPr>
    <w:rFonts w:ascii="黑体" w:hAnsi="黑体" w:eastAsia="黑体"/>
    <w:b/><w:sz w:val="28"/><w:szCs w:val="28"/>
  </w:rPr></w:pPr>
  <w:r><w:rPr>
    <w:rFonts w:ascii="黑体" w:hAnsi="黑体" w:eastAsia="黑体"/>
    <w:b/><w:sz w:val="28"/><w:szCs w:val="28"/>
  </w:rPr><w:t xml:space="preserve">十八、系统运行截图</w:t></w:r>
</w:p>'''

# We'll insert at sect19_new position. Build elements and insert before section 19
insert_target = list(body)[sect19_new]

# Also remove old stale images from section 19 (image3, image4, image5 in media)
# But keep the section 19 text content - just replace images

# For now, let me just remove section 18 and 19 images and replace with proper ones
# Let me do a simpler approach: edit the XML as text

print('Done with structural analysis')
tree.write(doc_file, xml_declaration=True, encoding='UTF-8')
print('Saved')
