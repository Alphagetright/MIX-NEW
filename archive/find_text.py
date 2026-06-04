#!/usr/bin/env python3
import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Desktop\pipeline_doc.docx', 'r')
doc = z.read('word/document.xml').decode('utf-8')
for m in re.finditer('CLI接口层', doc):
    start = max(0, m.start() - 150)
    end = min(len(doc), m.start() + 150)
    snippet = doc[start:end].replace('\n', '\\n')
    print(f'Position {m.start()}: ...{snippet}...\n')
z.close()
