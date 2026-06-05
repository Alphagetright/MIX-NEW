#!/usr/bin/env python3
"""Add missing image relationships to the pipeline doc."""
import zipfile, os, tempfile, shutil

path = r'C:\Users\Administrator\Desktop\pipeline_doc.docx'
IMG_DIR = r'C:\Users\Administrator\Desktop\All Mix'

# Read the rels file
z = zipfile.ZipFile(path, 'r')
rels = z.read('word/_rels/document.xml.rels').decode('utf-8')
z.close()

# Check which new rIds are missing
new_images = {
    'rId14': 'media/pipeline_cli_help.png',
    'rId15': 'media/pipeline_run.png',
    'rId16': 'media/pipeline_output.png',
    'rId17': 'media/p_login.png',
    'rId18': 'media/p_register.png',
    'rId19': 'media/p_dashboard.png',
    'rId20': 'media/p_home.png',
    'rId21': 'media/p_api_health.png',
}

missing = {}
for rid, target in new_images.items():
    if rid not in rels:
        missing[rid] = target
        print(f'  Missing: {rid} -> {target}')

if not missing:
    print('All relationships present!')
    exit(0)

# Add missing relationships before closing tag
insert = ''
for rid, target in missing.items():
    insert += '  <Relationship Id="%s" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="%s"/>\n' % (rid, target)

rels = rels.replace('</Relationships>', insert + '</Relationships>')

# Also ensure the new image files exist in the ZIP
# Since we injected images via lxml, python-docx didn't add them to media/
# We need to add them
image_files = {
    'word/media/pipeline_cli_help.png': os.path.join(IMG_DIR, 'pipeline_cli_help.png'),
    'word/media/pipeline_run.png': os.path.join(IMG_DIR, 'pipeline_run.png'),
    'word/media/pipeline_output.png': os.path.join(IMG_DIR, 'pipeline_output.png'),
    'word/media/p_login.png': os.path.join(IMG_DIR, 'p_login.png'),
    'word/media/p_register.png': os.path.join(IMG_DIR, 'p_register.png'),
    'word/media/p_dashboard.png': os.path.join(IMG_DIR, 'p_dashboard.png'),
    'word/media/p_home.png': os.path.join(IMG_DIR, 'p_home.png'),
    'word/media/p_api_health.png': os.path.join(IMG_DIR, 'p_api_health.png'),
}

# Rebuild the ZIP with updated rels and new media files
tmp = path + '.tmp'
with zipfile.ZipFile(path, 'r') as zin:
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.namelist():
            if item == 'word/_rels/document.xml.rels':
                # Write updated rels
                zout.writestr(item, rels)
            elif item in image_files:
                # Skip old image entries that will be replaced
                continue
            else:
                zout.writestr(item, zin.read(item))

        # Add new image files
        for arcname, local_path in image_files.items():
            if os.path.exists(local_path):
                zout.write(local_path, arcname)
                print(f'  Added: {arcname} ({os.path.getsize(local_path)} bytes)')
            else:
                print(f'  WARNING: {local_path} not found!')

os.replace(tmp, path)
print('Fixed!')
