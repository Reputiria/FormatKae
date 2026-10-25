# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / 'main.py')],
    pathex=[str(root)],
    binaries=[], datas=[(str(root / 'assets' / 'app.ico'), 'assets')], hiddenimports=[],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtNetwork', 'PySide6.QtOpenGL', 'PySide6.QtPdf', 'PySide6.QtTest', 'tkinter', 'unittest', 'PIL'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name='FormatKae',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False, target_arch='x86_64',
    icon=str(root / 'assets' / 'app.ico'), version=str(root / 'assets' / 'version.txt'),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='FormatKae')
