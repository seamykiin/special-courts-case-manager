# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files, collect_dynamic_libs

block_cipher = None

# Collect all files for PyQt6
pyqt6_datas, pyqt6_binaries, pyqt6_hiddenimports = collect_all('PyQt6')

# Collect all files for webview, clr_loader, pythonnet
webview_datas, webview_binaries, webview_hiddenimports = collect_all('webview')

try:
    clr_datas, clr_binaries, clr_hiddenimports = collect_all('clr_loader')
except Exception:
    clr_datas, clr_binaries, clr_hiddenimports = [], [], []

try:
    pnet_datas, pnet_binaries, pnet_hiddenimports = collect_all('pythonnet')
except Exception:
    pnet_datas, pnet_binaries, pnet_hiddenimports = [], [], []

added_files = [
    ('index.html', '.'),
    ('server.py', '.'),
    ('case.py', '.'),
]

if os.path.exists('sample_cause_list.csv'):
    added_files.append(('sample_cause_list.csv', '.'))

if os.path.exists('pending_cases.db'):
    added_files.append(('pending_cases.db', '.'))

if os.path.exists('geo_data.json'):
    added_files.append(('geo_data.json', '.'))

all_datas = (
    added_files
    + pyqt6_datas
    + webview_datas
    + clr_datas
    + pnet_datas
)

all_binaries = (
    pyqt6_binaries
    + webview_binaries
    + clr_binaries
    + pnet_binaries
)

raw_hiddenimports = (
    [
        'http.server',
        'urllib.request',
        'urllib.parse',
        'urllib.error',
        'sqlite3',
        'json',
        'csv',
        'base64',
        'shutil',
        'threading',
        'socket',
        'server',
        'case',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'webview',
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets',
        'clr',
        'pythonnet',
        'clr_loader',
        'cffi',
    ]
    + pyqt6_hiddenimports
    + webview_hiddenimports
    + clr_hiddenimports
    + pnet_hiddenimports
)

# Filter out invalid module names (e.g. filenames containing hyphens or ending in .py)
all_hiddenimports = list(set([
    h for h in raw_hiddenimports
    if h and '-' not in h and not h.endswith('.py') and not h.endswith('.tcl')
]))

a = Analysis(
    ['desktop_app.py'],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'numpy', 'torch'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LGCCaseRegister',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='LGCCaseRegister',
)
