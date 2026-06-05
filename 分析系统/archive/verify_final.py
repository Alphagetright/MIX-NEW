#!/usr/bin/env python3
import zipfile, os, xml.etree.ElementTree as ET
path = r'C:\Users\Administrator\Desktop\pipeline_doc.docx'
z = zipfile.ZipFile(path, 'r')
print('File: %d bytes, %d entries' % (os.path.getsize(path), len(z.namelist())))
media = sorted([n for n in z.namelist() if 'media/' in n])
for m in media:
    info = z.getinfo(m)
    fname = m.split('/')[-1]
    print('  %s: %7d bytes' % (fname, info.file_size))
rels = z.read('word/_rels/document.xml.rels').decode('utf-8')
rid_count = rels.count('Relationship Id=')
print('Relationships:', rid_count)
doc = z.read('word/document.xml').decode('utf-8')
for i in range(1, 8):
    label = '图%d：' % i
    cnt = doc.count(label)
    print('  "%s": %d occurrence(s)' % (label, cnt))
try:
    ET.fromstring(doc.encode('utf-8'))
    print('  document.xml: valid XML')
except Exception as e:
    print('  document.xml: ERROR -', e)
z.close()
print('Done!')
