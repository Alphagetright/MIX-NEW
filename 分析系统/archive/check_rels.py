#!/usr/bin/env python3
import zipfile, re
path = r'C:\Users\Administrator\Desktop\pipeline_doc.docx'
z = zipfile.ZipFile(path, 'r')
rels = z.read('word/_rels/document.xml.rels').decode('utf-8')
for m in re.finditer(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels):
    print(m.group(1), '->', m.group(2))
z.close()
