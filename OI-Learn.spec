# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('data', 'data'), ('assets', 'assets')],
    hiddenimports=['markdown', 'markdown.extensions.fenced_code', 'markdown.extensions.codehilite', 'markdown.extensions.tables', 'markdown.extensions.toc', 'pygments', 'pygments.lexers', 'pygments.formatters', 'requests', 'urllib3', 'certifi', 'charset_normalizer', 'idna', 'modules.home', 'modules.outline', 'modules.plan', 'modules.contest', 'modules.problems', 'modules.templates', 'modules.mistakes', 'modules.encyclopedia', 'modules.stats', 'modules.settings', 'modules.problem_meta', 'components.markdown_view', 'components.code_editor', 'db.database', 'db.seed', 'services.fetcher', 'services.contests', 'services.exporter', 'services.markdown_engine'],
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
    name='OI-Learn',
    icon='assets/app_icon.png',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
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
    name='OI-Learn',
)
