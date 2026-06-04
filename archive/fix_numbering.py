#!/usr/bin/env python3
"""Fix heading numbering: disable auto-numbering on all headings."""
from docx import Document
from docx.oxml.ns import qn
from lxml import etree
import shutil, os

DST = r'C:\Users\Administrator\Desktop\pipeline_doc.docx'

doc = Document(DST)
fixed = 0

for p in doc.paragraphs:
    if p.style and p.style.name and 'Heading' in p.style.name:
        pPr = p._element.find(qn('w:pPr'))
        if pPr is None:
            pPr = etree.SubElement(p._element, qn('w:pPr'))
            # Move to front
            p._element.insert(0, p._element.remove(pPr))

        # Remove any existing numPr
        for numPr in pPr.findall(qn('w:numPr')):
            pPr.remove(numPr)

        # Add numPr with numId=0 to explicitly disable numbering
        numPr = etree.SubElement(pPr, qn('w:numPr'))
        numId = etree.SubElement(numPr, qn('w:numId'))
        numId.set(qn('w:val'), '0')

        fixed += 1

doc.save(DST)
print(f'Fixed {fixed} headings - disabled auto-numbering')
