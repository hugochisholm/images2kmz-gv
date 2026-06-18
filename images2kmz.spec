# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for images2kmz Windows EXE (--onefile)."""

from PyInstaller.utils.hooks import collect_all, collect_data_files
import pyproj.datadir

# Collect packages that need special handling at bundle time
textual_datas, textual_binaries, textual_hiddenimports = collect_all('textual')
heif_datas, heif_binaries, heif_hiddenimports = collect_all('pillow_heif')

# PROJ coordinate database bundled with pyproj
proj_data_dir = pyproj.datadir.get_data_dir()

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=[
        *heif_binaries,
    ],
    datas=[
        # Bundled pin icons (loaded via Path(__file__).parent / 'icons' in core.py)
        ('src/images2kmz/icons', 'images2kmz/icons'),
        # PROJ coordinate transformation database (pyproj runtime hook sets PROJ_DATA)
        (proj_data_dir, 'proj'),
        *textual_datas,
        *heif_datas,
    ],
    hiddenimports=[
        # All images2kmz submodules (some are imported lazily)
        'images2kmz',
        'images2kmz.cli',
        'images2kmz.core',
        'images2kmz.image_processor',
        'images2kmz.csv_exporter',
        'images2kmz.heic_handler',
        'images2kmz.placemark_config',
        'images2kmz.placemark_html_builder',
        'images2kmz.logging_config',
        'images2kmz.progress',
        'images2kmz.tui',
        'images2kmz.ui_handler',
        'images2kmz.utils',
        # Third-party
        'pyproj',
        'pyproj.transformer',
        'pyproj.crs',
        'pyproj.datadir',
        'exifread',
        'simplekml',
        'GPSPhoto',
        'piexif',
        *textual_hiddenimports,
        *heif_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hooks/rthook_pyproj.py'],
    excludes=[
        'tkinter',
        'unittest',
        'email',
        'html',
        'http',
        'urllib',
        'xml',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='images2kmz',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,   # disabled: UPX can trigger AV false-positives
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
