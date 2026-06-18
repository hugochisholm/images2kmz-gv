#!/usr/bin/env python3
"""
Main entry point for images2kmz command-line tool.

This script can be run directly to generate KMZ files from geotagged photos.
"""

from multiprocessing import freeze_support

from images2kmz.cli import main

if __name__ == '__main__':
    freeze_support()
    main()
