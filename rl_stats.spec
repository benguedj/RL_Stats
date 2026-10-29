# -*- mode: python ; coding: utf-8 -*-
# Build : pyinstaller rl_stats.spec  (ou build.bat)

import re

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo, VarStruct, VSVersionInfo)

# Metadonnees de l'exe (Proprietes > Details), version lue dans rl_stats.pyw
with open('rl_stats.pyw', encoding='utf-8') as f:
    APP_VERSION = re.search(r'^APP_VERSION = "(.+)"', f.read(), re.M).group(1)
numbers = tuple(int(n) for n in APP_VERSION.split('.')) + (0,)
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=numbers, prodvers=numbers),
    kids=[
        StringFileInfo([StringTable('040904B0', [
            StringStruct('CompanyName', 'Benjamin Guedj'),
            StringStruct('FileDescription', 'RL Stats'),
            StringStruct('FileVersion', APP_VERSION),
            StringStruct('InternalName', 'RL Stats'),
            StringStruct('LegalCopyright', 'Copyright (c) 2026 Benjamin Guedj. MIT License.'),
            StringStruct('OriginalFilename', 'RL Stats.exe'),
            StringStruct('ProductName', 'RL Stats'),
            StringStruct('ProductVersion', APP_VERSION),
        ])]),
        VarFileInfo([VarStruct('Translation', [0x0409, 1200])]),
    ],
)

a = Analysis(
    ['rl_stats.pyw'],
    pathex=['.'],
    binaries=[],
    datas=[('rl_stats.ico', '.')],
    hiddenimports=['winrt.windows.applicationmodel', 'winrt.windows.foundation'],
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
    name='RL Stats',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX provoque des faux positifs antivirus
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['rl_stats.ico'],
    version=version_info,
)
