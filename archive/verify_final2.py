#!/usr/bin/env python3
import zipfile, os, re, xml.etree.ElementTree as ET
path = r'C:\Users\Administrator\Desktop\pipeline_doc.docx'
z = zipfile.ZipFile(path, 'r')
print('File: %d bytes, %d entries' % (os.path.getsize(path), len(z.namelist())))
print('All files:', z.namelist())
# Check rels
rels = z.read('word/_rels/document.xml.rels').decode('utf-8')
print('\nRelationships:')
for m in re.finditer(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels):
    print('  %s -> %s' % (m.group(1), m.group(2)))
# Check document body references
doc = z.read('word/document.xml').decode('utf-8')
used_rids = set(re.findall(r'embed="(rId\d+)"', doc))
print('\nrIds referenced in body:', sorted(used_rids))
# Verify each referenced rid exists in rels
for rid in sorted(used_rids):
    if rid in rels:
        print('  %s: OK' % rid)
    else:
        print('  %s: MISSING in rels!' % rid)
# Check figure labels
for i in range(1, 8):
    label = '图%d：' % i
    cnt = doc.count(label)
    print('  "%s": %d times' % (label, cnt))
# Verify media files exist for referenced images
media_files = [n for n in z.namelist() if 'media/' in n]
print('\nMedia files:', len(media_files))
for m in sorted(media_files):
    info = z.getinfo(m)
    print('  %s (%d bytes)' % (m.split('/')[-1], info.file_size))
# XML valid
try:
    ET.fromstring(doc.encode('utf-8'))
    print('\nXML: valid')
except Exception as e:
    print('\nXML ERROR:', e)
# python-docx open
try:
    from docx import Document
    d = Document(path)
    print('python-docx open: OK (%d paragraphs)' % len(d.paragraphs))
except Exception as e:
    print('python-docx ERROR:', e)
z.close()
print('\nDone!')
