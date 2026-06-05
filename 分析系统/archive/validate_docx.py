#!/usr/bin/env python3
"""Comprehensive DOCX validation."""
import zipfile, os, sys
from xml.etree import ElementTree as ET

path = r'C:\Users\Administrator\Desktop\pipeline_doc.docx'
print(f'Checking: {path}')
print(f'File size: {os.path.getsize(path)} bytes')

z = zipfile.ZipFile(path, 'r')
names = z.namelist()
print(f'ZIP entries: {len(names)}')

# 1. Check [Content_Types].xml
ct = z.read('[Content_Types].xml').decode('utf-8')
print(f'\n[Content_Types].xml: {len(ct)} chars')
if 'image/png' not in ct:
    print('  ERROR: image/png content type missing!')
else:
    print('  image/png: OK')
if 'image/jpeg' not in ct:
    print('  WARNING: image/jpeg content type missing (may use jpeg thumbnail)')

# 2. Check document.xml body
doc = z.read('word/document.xml').decode('utf-8')
if '<w:body>' in doc and '</w:body>' in doc:
    body_start = doc.index('<w:body>')
    body_end = doc.index('</w:body>')
    body = doc[body_start:body_end+len('</w:body>')]
    print(f'\ndocument.xml body: {len(body)} chars')
else:
    print('\nERROR: body tags not found!')

# 3. Verify all rels targets exist
rels = z.read('word/_rels/document.xml.rels').decode('utf-8')
print(f'\nRelationships:')
root = ET.fromstring(rels)
ns = {'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}
for rel in root.findall('r:Relationship', ns):
    target = rel.get('Target')
    if target and 'media/' in target:
        if target not in [n for n in names]:
            print(f'  ERROR: {rel.get("Id")} -> {target} (FILE MISSING!)')
        else:
            info = z.getinfo(target)
            print(f'  {rel.get("Id")} -> {target} ({info.file_size} bytes)')

# 4. Try to parse document.xml with lxml for strict validation
try:
    import lxml.etree as LXML
    LXML.fromstring(doc.encode('utf-8'))
    print('\nlxml parse: OK')
except ImportError:
    print('\nlxml not available, trying ElementTree')
    try:
        ET.fromstring(doc.encode('utf-8'))
        print('ElementTree parse: OK')
    except Exception as e:
        print(f'ElementTree parse ERROR: {e}')

# 5. Check for common issues
issues = []
if '<!--' in doc:
    issues.append('HTML-style comments in XML')
# Check no stray curly braces from Python f-strings
if '{' in doc and 'http://' not in doc[doc.index('{'):doc.index('{')+20]:
    # Find all { not followed by http
    import re
    braces = [(m.start(), doc[m.start():m.start()+50]) for m in re.finditer('[{}]', doc)
              if not doc[m.start():m.start()+20].startswith('{http')]
    if braces:
        issues.append(f'Suspicious braces: {len(braces)} found')

if issues:
    print(f'\nIssues found:')
    for i in issues:
        print(f'  - {i}')
else:
    print('\nNo issues found!')

z.close()
print('\nValidation complete!')
