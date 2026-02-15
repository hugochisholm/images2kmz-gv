# images2kmz Project Guide

Python CLI tool for creating KMZ (Google Earth) files from geotagged photos.

## Project Commands

### Testing

**All test commands must be run within the project's virtual environment (./.venv/):**

```bash
# First, activate the virtual environment
source ./.venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate  # On Windows

# Run all tests
pytest

# Run single test file
pytest tests/test_core.py

# Run specific test class
pytest tests/test_core.py::TestKMZGeneratorInit

# Run single test
pytest tests/test_core.py::TestKMZGeneratorInit::test_kmz_generator_initialization

# Run with coverage
pytest --cov=images2kmz

# Run with verbose output
pytest -v

# Run specific test by keyword
pytest -k test_kmz_generator

# Run with fail-fast (stop on first failure)
pytest -x
```

### Installation & Running

**Note: Always use the project's virtual environment located at `./.venv/`:**

```bash
# Activate the virtual environment first
source ./.venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate  # On Windows

# Then run any Python commands:

# Install in development mode
pip install -e .

# Install dev dependencies
pip install -r requirements-dev.txt

# Run the CLI
python -m images2kmz

# Or use the installed command
images2kmz
```

## Code Style Guidelines

### Imports
- **Standard library** first (sorted alphabetically)
- **Third-party** packages second
- **Local modules** third
- Use explicit imports: `from pathlib import Path` not `from pathlib import *`
- Type hints: Prefer modern built-in generics (Python 3.10+)
- Internal imports: `from images2kmz.core import KMZGenerator`

**Modern Type Hints (Python 3.10+):**
```python
from __future__ import annotations
import argparse
import os
import tempfile
from pathlib import Path
from collections.abc import Callable  # Modern way for callable types

def process_photos(paths: list[str | Path]) -> dict[str, bool]:
    result: dict[str, bool] = {}
    return result

def get_photo(path: str | Path) -> Image | None:
    ...
```

**Legacy Type Hints (Python <3.10 compatibility):**
```python
from typing import List, Dict, Optional, Callable, Union

def process_photos(paths: List[Union[str, Path]]) -> Dict[str, bool]: ...
def get_photo(path: Union[str, Path]) -> Optional[Image]: ...
```

**Import Order Example:**
```python
import argparse
import os
import tempfile
from pathlib import Path

from PIL import Image
from rich.console import Console

from images2kmz.core import KMZGenerator
from images2kmz.image_processor import ImageProcessor
```

### Formatting & Types
- Type hints **required** for all function parameters and return values
- Use `from __future__ import annotations` for forward references
- Google-style docstrings for public APIs:
```python
def add_photo(self, photo_path: Path, description: str | None = None) -> bool:
    """Add a photo to the KMZ.

    Args:
        photo_path: Path to the photo file
        description: Optional HTML description for the placemark

    Returns:
        True if photo added successfully, False otherwise
    """
```
- Line length: ~100 characters (practical limit, not strict)
- No enforced formatter (no black/flake8 config found)

### Naming Conventions
- **Classes**: PascalCase (`KMZGenerator`, `ImageProcessor`)
- **Functions/Methods**: snake_case (`add_photo`, `process_directory`)
- **Variables**: snake_case (`photo_path`, `output_kmz`)
- **Constants**: UPPER_CASE (`SUPPORTED_FORMATS`, `DEFAULT_ICON_SIZE`)
- **Private methods**: single underscore prefix (`_cleanup_temp`)
- **Boolean-returning functions**: use `is_` or `has_` prefix (`is_supported_format()`)

### Error Handling
- **Silent failure pattern**: Return `None` or `False` on recoverable errors
- Use `try/except` for external operations (file I/O, image processing)
- Log errors via `rich.console.Console.print()` with `[red]` styling
- Exit codes: 0 (success), 1 (error), 130 (user interrupted)
- Never propagate exceptions to user - handle gracefully

Example:
```python
try:
    image = Image.open(photo_path)
except Exception as e:
    console.print(f"[red]Error loading image: {e}[/red]")
    return False
```

### Project Structure (Modern src Layout)

The project uses the modern src layout structure:

```
images2kmz/
├── src/
│   └── images2kmz/        # Source package
│       ├── __init__.py    # Package init
│       ├── __main__.py    # python -m images2kmz entry point
│       ├── cli.py         # CLI interface (argparse + rich)
│       ├── core.py        # Core KMZGenerator class
│       ├── image_processor.py   # Image processing (GPS extraction, thumbnails)
│       ├── heic_handler.py      # HEIC format conversion
│       ├── progress.py          # Progress display utilities
│       └── utils.py             # Utility functions (paths, formatting)
├── tests/
│   ├── conftest.py        # pytest fixtures
│   ├── test_core.py       # Core functionality tests
│   ├── test_cli.py        # CLI tests
│   ├── test_image_processor.py
│   ├── test_heic_handler.py
│   ├── test_progress.py
│   └── test_utils.py
├── setup.py               # Package configuration
├── README.md
└── requirements*.txt
```

### Key Patterns

**Callback Pattern**: Use callbacks for progress updates
```python
Callback = Callable[[int, int, str], None]  # current, total, message
```

**Stats Tracking**: Track operation stats in dedicated class
```python
class ImageProcessorStats:
    total_found: int = 0
    processed: int = 0
    skipped_no_gps: int = 0
    errors: int = 0
```

**Class Design**: Use dataclasses for simple data containers
```python
from dataclasses import dataclass

@dataclass
class GPSData:
    latitude: float
    longitude: float
    altitude: float | None = None
```

**CLI Pattern**: Return exit codes, handle KeyboardInterrupt
```python
try:
    result = run()
    return result
except KeyboardInterrupt:
    console.print("\n[yellow]Operation cancelled by user[/yellow]")
    return 130
```

### Dependencies
- **Core**: GPSPhoto, Pillow, simplekml, rich, textual, piexif, pillow-heif
- **Testing**: pytest, pytest-cov
- **Linting/Formatting** (recommended to add):
  - `ruff>=0.1.0` - Fast Python linter and formatter
  - `mypy>=1.0` - Static type checker
  - Consider migrating from setup.py to pyproject.toml

### File I/O
- Use `pathlib.Path` for all path operations
- Create temp files with `tempfile.mkdtemp()` for thumbnails
- Clean up temp files in `__del__` or explicit `cleanup()` methods

### Git
- Never commit: `*.kmz`, `*.kml`, sample images (see .gitignore)
- Never auto-commit - wait for explicit user instruction
