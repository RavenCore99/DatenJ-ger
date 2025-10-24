# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['v10_v4.py'],
    pathex=[],
    binaries=[],
    datas=[('logo.png', '.'), ('base_datos_pdfs.db', '.')],
    hiddenimports=['PIL._tkinter_finder', 'PIL.ImageTk', 'PIL.Image', 'tkinter'],
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
    name='DatenJäger_64bit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='x86_64',
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo.ico'],
)
