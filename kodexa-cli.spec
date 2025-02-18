# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['kodexa_cli/cli.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'click',
        'click.termui',
        'click.types',
        'rich',
        'rich.console',
        'rich.table',
        'rich.prompt'
    ],
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
    a.binaries,
    a.datas,
    [],
    name='kodexa',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
