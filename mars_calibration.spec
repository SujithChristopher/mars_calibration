# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# Get the project root directory
project_root = Path.cwd()

# Define data files to include
added_files = [
    # Arduino sketches
    (str(project_root / 'loadcell_calibration'), 'loadcell_calibration'),
    (str(project_root / 'firmware'), 'firmware'), 
    (str(project_root / 'imu_program_teensy'), 'imu_program_teensy'),
    
    # Any additional data files
    (str(project_root / 'README.md'), '.'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtWidgets', 
    'PySide6.QtGui',
    'serial',
    'serial.tools.list_ports',
    'toml',
    'requests',
    'zipfile',
    'tarfile',
    'json',
    'pathlib',
    'glob',
    'platform',
    'shutil',
    'threading',
    'datetime',
    'subprocess'
]

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=added_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove unnecessary files to reduce size
a.datas = [x for x in a.datas if not x[0].startswith('tcl')]
a.datas = [x for x in a.datas if not x[0].startswith('tk')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MarsCalibration',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add path to .ico file if you have one
    version_file=None,  # Add version info file if needed
)