# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['kodexa_cli/cli.py'],
    pathex=['.'],
    binaries=[],
    datas=[('kodexa_cli', 'kodexa_cli')],
    hiddenimports=[
        'kodexa_cli',
        'kodexa_cli.cli',
        'kodexa_cli.commands',
        'kodexa_cli.platform',
        'click.core',
        'click.decorators',
        'click.parser',
        'click.formatting',
        'click.termui',
        'rich.console',
        'rich.theme',
        'rich.text',
        'rich.markup',
        'rich.logging',
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
        'rich.padding',
        'rich.logging',
        'rich.traceback',
        'rich.pretty'
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
    [('kodexa', 'kodexa_cli/cli.py', 'PYSOURCE')],
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='kodexa',
    runtime_tmpdir=None,
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    upx_exclude=[],
    runtime_tmpdir=None,
    entitlements_file=None,
)
