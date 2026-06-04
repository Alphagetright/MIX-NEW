#!/usr/bin/env python3
"""Fix image paths in DOCX - move from root media/ to word/media/."""
import zipfile, os, shutil

path = r'C:\Users\Administrator\Desktop\pipeline_doc.docx'
IMG_DIR = r'C:\Users\Administrator\Desktop\All Mix'

new_images = {
    'word/media/pipeline_cli_help.png': os.path.join(IMG_DIR, 'pipeline_cli_help.png'),
    'word/media/pipeline_run.png': os.path.join(IMG_DIR, 'pipeline_run.png'),
    'word/media/pipeline_output.png': os.path.join(IMG_DIR, 'pipeline_output.png'),
    'word/media/p_login.png': os.path.join(IMG_DIR, 'p_login.png'),
    'word/media/p_register.png': os.path.join(IMG_DIR, 'p_register.png'),
    'word/media/p_dashboard.png': os.path.join(IMG_DIR, 'p_dashboard.png'),
    'word/media/p_home.png': os.path.join(IMG_DIR, 'p_home.png'),
    'word/media/p_api_health.png': os.path.join(IMG_DIR, 'p_api_health.png'),
}

tmp = path + '.tmp'
with zipfile.ZipFile(path, 'r') as zin:
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.namelist():
            # Skip the wrong-path files at root media/
            if item.startswith('media/') and not item.startswith('word/media/'):
                print('  Skip root:', item)
                continue
            zout.writestr(item, zin.read(item))
        # Add new images at correct path
        for arcname, local_path in new_images.items():
            zout.write(local_path, arcname)
            print('  Add:', arcname, '(%d bytes)' % os.path.getsize(local_path))

os.replace(tmp, path)
print('\nDone!')
