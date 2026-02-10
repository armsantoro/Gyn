# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file per GynTracker
# Uso: pyinstaller app.spec

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Raccogli i dati necessari per Streamlit e Plotly
streamlit_data = collect_data_files('streamlit')
plotly_data = collect_data_files('plotly')

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('database.py', '.'),
    ] + streamlit_data + plotly_data,
    hiddenimports=[
        'streamlit',
        'plotly',
        'pandas',
        'openpyxl',
        'sqlite3',
    ] + collect_submodules('streamlit') + collect_submodules('plotly'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GynTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
