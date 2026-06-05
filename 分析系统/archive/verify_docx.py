#!/usr/bin/env python3
import zipfile, re, xml.etree.ElementTree as ET

path = 'C:/Users/Administrator/Desktop/新建文件夹 (14)/软著_古典诗歌文本结构化标注生产系统_软件说明书.docx'
z = zipfile.ZipFile(path, 'r')
print('Files in ZIP:', z.namelist())

doc = z.read('word/document.xml').decode('utf-8')
rels = z.read('word/_rels/document.xml.rels').decode('utf-8')

print(f'\ndocument.xml: {len(doc)} chars')

# Check images in rels
for rid in ['rId14','rId15','rId16','rId17','rId18','rId19','rId20','rId21']:
    m = re.search('Id="' + rid + '"[^>]*Target="([^"]+)"', rels)
    if m:
        print(f'  {rid} -> {m.group(1)}')
    else:
        print(f'  {rid}: MISSING!')

# Check content
for s in ['十八、系统运行截图', '图1：', '图7：', 'rId17', 'rId21', 'p_login.png', 'p_dashboard.png']:
    print(f'  "{s}": {"OK" if s in doc else "MISSING"}')

# Check old images
for rid in ['rId11','rId12','rId13']:
    count = doc.count(rid)
    if count:
        print(f'  old {rid}: {count} reference(s) STILL in body!')
    else:
        print(f'  old {rid}: removed OK')

# XML parse check
try:
    ET.fromstring(doc)
    print('  XML parsing: OK')
except Exception as e:
    print(f'  XML ERROR: {e}')

# Check media files exist
media = [n for n in z.namelist() if 'media' in n]
print(f'\nMedia files ({len(media)}):')
for m in sorted(media):
    info = z.getinfo(m)
    print(f'  {m.split("/")[-1]} ({info.file_size} bytes)')

z.close()
print('\nVerification complete!')
