"""Entry point for the images2kmz package.

This module serves as the package entry point when running:
    python -m images2kmz

It delegates execution to the main CLI function defined in cli.py.

Example:
    $ python -m images2kmz --help
    $ python -m images2kmz /path/to/photos --output result.kmz
"""

"""Entry point for running images2kmz as a module.

This module allows the package to be executed directly using:
    python -m images2kmz

It serves as the main entry point when the package is run as a script,
delegating to the CLI main function for argument parsing and execution.
"""

from .cli import main

if __name__ == '__main__':
    main()
