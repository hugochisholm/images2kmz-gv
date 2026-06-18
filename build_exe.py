#!/usr/bin/env python3
"""Build script: produces dist/images2kmz.exe via PyInstaller.

Run from the project root on a Windows machine (or in CI):
    python build_exe.py

Requirements:
    pip install pyinstaller
    pip install -e .
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SPEC = Path(__file__).parent / 'images2kmz.spec'
OUT  = Path(__file__).parent / 'dist' / 'images2kmz.exe'


def main() -> int:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller not found. Install it with:  pip install pyinstaller")
        return 1

    cmd = [sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm', str(SPEC)]
    print(f"Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"\nBuild FAILED (exit code {result.returncode})")
        return result.returncode

    if OUT.exists():
        size_mb = OUT.stat().st_size / (1024 * 1024)
        print(f"\nBuild successful: {OUT}  ({size_mb:.1f} MB)")
    else:
        print(f"\nBuild finished but expected output not found: {OUT}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
