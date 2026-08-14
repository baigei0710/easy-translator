# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['easy-translator.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pynput.keyboard', 'pynput.mouse', 'pynput.keyboard._darwin', 'pynput.mouse._darwin'],
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
    name='EasyTranslator',
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
    name='EasyTranslator',
)
app = BUNDLE(
    coll,
    name='EasyTranslator.app',
    icon=None,
    bundle_identifier=None,
)
