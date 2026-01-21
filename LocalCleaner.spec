# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Local Cleaner
Generates a standalone Windows executable with all dependencies bundled.
"""

import sys
import glob
from pathlib import Path

# Application metadata
APP_NAME = "LocalCleaner"
APP_VERSION = "1.1.0"
APP_AUTHOR = "Emilio Ranucoli"

# Paths
ROOT_DIR = Path(SPECPATH)
SRC_DIR = ROOT_DIR / "src"
RESOURCES_DIR = ROOT_DIR / "resources"
ICON_PATH = RESOURCES_DIR / "icon.ico"

# Check if icon exists, use default if not
icon_file = str(ICON_PATH) if ICON_PATH.exists() else None

block_cipher = None

# Build datas list dynamically - only include files that exist
datas = []

# Add QSS files if they exist
qss_files = list(RESOURCES_DIR.glob('*.qss'))
for f in qss_files:
    datas.append((str(f), 'resources'))

# Add JSON files from resources if they exist  
json_files = list(RESOURCES_DIR.glob('*.json'))
for f in json_files:
    datas.append((str(f), 'resources'))

# Add icon if exists
ico_files = list(RESOURCES_DIR.glob('*.ico'))
for f in ico_files:
    datas.append((str(f), 'resources'))

# Add PNG files if they exist
png_files = list(RESOURCES_DIR.glob('*.png'))
for f in png_files:
    datas.append((str(f), 'resources'))

# Add config.json if exists
config_file = ROOT_DIR / 'config.json'
if config_file.exists():
    datas.append((str(config_file), '.'))

a = Analysis(
    ['main.py'],
    pathex=[str(ROOT_DIR), str(SRC_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui', 
        'PySide6.QtWidgets',
        'sqlite3',
        'psutil',
        'send2trash',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'cv2',
        'scipy',
        'IPython',
        'jupyter',
    ],
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
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window - GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
    version='version_info.txt' if Path('version_info.txt').exists() else None,
)
