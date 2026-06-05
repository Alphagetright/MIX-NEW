# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\Administrator\\Desktop\\All Mix\\cli_ops\\launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\Administrator\\Desktop\\All Mix\\poem_json', 'poem_json'), ('C:\\Users\\Administrator\\Desktop\\All Mix\\dufu/poem-json', 'dufu/poem-json'), ('C:\\Users\\Administrator\\Desktop\\All Mix\\poem_lab/prompts', 'poem_lab/prompts'), ('C:\\Users\\Administrator\\Desktop\\All Mix\\poem_lab/templates', 'poem_lab/templates'), ('C:\\Users\\Administrator\\Desktop\\All Mix\\cli_ops/web/templates', 'cli_ops_web_templates')],
    hiddenimports=['cli_ops', 'cli_ops.cli_main', 'cli_ops.repl', 'cli_ops.session', 'cli_ops.rich_ui', 'cli_ops.tools', 'cli_ops.agent_loop', 'cli_ops.llm_client', 'cli_ops.models', 'cli_ops.config', 'cli_ops.logger', 'cli_ops.errors', 'cli_ops.utils', 'cli_ops.validators', 'cli_ops.cache_manager', 'cli_ops.export_engine', 'cli_ops.data_scanner', 'cli_ops.health_checker', 'cli_ops.report_generator', 'cli_ops.batch_processor', 'cli_ops.preprocessor', 'cli_ops.monitor', 'cli_ops.web', 'cli_ops.web.app', 'poem_lab', 'poem_lab.app', 'poem_lab.lib', 'poem_lab.lib.meta_prompts', 'poem_lab.lib.schema_engine', 'poem_lab.lib.llm_client', 'poem_lab.lib.config_loader', 'poem_lab.lib.persistence', 'poem_lab.lib.quality_scorer', 'poem_lab.lib.report_writer', 'poem_lab.lib.annotation_tools', 'poem_lab.lib.template_library', 'poem_lab.lib.corpus', 'poem_lab.lib.preprocessor', 'flask', 'rich', 'chromadb', 'requests', 'openpyxl'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TangCLI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TangCLI',
)
