"""Entry point for the images2kmz package.

This module serves as the package entry point when running:
    python -m images2kmz

It delegates execution to the main CLI function defined in cli.py.

Example:
    $ python -m images2kmz --help
    $ python -m images2kmz /path/to/photos --output result.kmz
"""

from multiprocessing import freeze_support

from .cli import main

if __name__ == '__main__':
    freeze_support()
    main()
