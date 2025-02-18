# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['kodexa_cli/cli.py'],
    pathex=['.'],
    binaries=[],
    datas=[('kodexa_cli', 'kodexa_cli')],
    hiddenimports=[
        'kodexa_cli',
        'kodexa_cli.cli',
        'click',
        'click.termui',
        'click.types',
        'click._compat',
        'click.formatting',
        'click.parser',
        'click.core',
        'click.decorators',
        'click.utils',
        'click.exceptions',
        'rich',
        'rich.console',
        'rich.table',
        'rich.prompt',
        'rich.text',
        'rich.style',
        'rich.theme',
        'rich.terminal_theme',
        'rich.box',
        'rich.color',
        'rich.markup',
        'rich.padding'
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
    a.scripts + [('kodexa', 'kodexa_cli/cli.py', 'PYSOURCE')],
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
