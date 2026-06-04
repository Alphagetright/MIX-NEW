#!/usr/bin/env python3
"""Check heading numbering in the document."""
import zipfile, re

path = r'C:\Users\Administrator\Desktop\pipeline_doc.docx'
z = zipfile.ZipFile(path, 'r')

# Check numbering.xml
num = z.read('word/numbering.xml').decode('utf-8')
print('=== Numbering.xml headings ===')
for line in num.splitlines():
    if 'Heading' in line or 'heading' in line:
        print(' ', line.strip()[:150])

# Check styles.xml for numId on Heading styles
sty = z.read('word/styles.xml').decode('utf-8')
print('\n=== Heading styles with numId ===')
for m in re.finditer(r'<w:style w:type="paragraph" w:styleId="Heading[12]".*?</w:style>', sty, re.DOTALL):
    block = m.group()
    if 'numId' in block:
        print(' HAS numId:', block[:300])
    else:
        print(' No numId:', block[:200])

# Check actual headings in doc
doc = z.read('word/document.xml').decode('utf-8')
print('\n=== Actual headings ===')
for m in re.finditer(r'<w:pStyle w:val="(Heading[12])".*?<w:t[^>]*>(.*?)</w:t>', doc, re.DOTALL):
    style = m.group(1)
    text = m.group(2)
    # Get context to see if there's numbering override
    context_start = max(0, m.start() - 200)
    context = doc[context_start:m.start()]
    has_numid = 'numId' in context
    print(f' [{style}] {text[:60]} (numId in pPr: {has_numid})')

z.close()
