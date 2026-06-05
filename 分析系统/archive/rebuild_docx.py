#!/usr/bin/env python3
"""Rebuild DOCX from unpacked directory directly."""
import zipfile, os

unpacked = r'C:\Users\Administrator\Desktop\新建文件夹 (14)\unpacked_pipe_new'
output = r'C:\Users\Administrator\Desktop\pipeline_doc.docx'

# Get all files from unpacked directory
files_to_add = []
for root, dirs, files in os.walk(unpacked):
    for f in files:
        full = os.path.join(root, f)
        arcname = os.path.relpath(full, unpacked)
        files_to_add.append((full, arcname))

files_to_add.sort(key=lambda x: x[1])

with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
    for full, arcname in files_to_add:
        z.write(full, arcname)
        # Print first 5 and last 5
        # print(f'  {arcname} ({os.path.getsize(full)} bytes)')

print(f'Created: {output}')
print(f'Files: {len(files_to_add)}')
print(f'Size: {os.path.getsize(output)} bytes')
