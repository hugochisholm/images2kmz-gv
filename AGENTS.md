# AGENTS.md - Developer Guide for images2kmz

This file provides guidelines for agentic coding assistants working in the images2kmz repository.

## Table of Contents

- [Project Overview](#project-overview)
- [Build & Run Commands](#build--run-commands)
  - [Setup](#setup)
  - [Run](#run)
  - [Testing](#testing)
  - [Linting & Formatting](#linting--formatting)
- [Code Style Guidelines](#code-style-guidelines)
  - [Imports](#imports)
  - [Type Hints](#type-hints)
  - [Naming Conventions](#naming-conventions)
  - [Docstrings](#docstrings)
  - [Error Handling](#error-handling)
  - [Formatting](#formatting)
- [Project-Specific Patterns](#project-specific-patterns)
  - [Temporary File Management](#temporary-file-management)
  - [Optional Dependencies](#optional-dependencies)
  - [CLI Exit Codes](#cli-exit-codes)
  - [EXIF Orientation Handling](#exif-orientation-handling)
  - [Cross-Platform Path Handling](#cross-platform-path-handling)
- [Module Structure](#module-structure)
- [Common Development Tasks](#common-development-tasks)
- [Testing Guidelines](#testing-guidelines)
- [Debugging Tips](#debugging-tips)
- [Additional Notes](#additional-notes)

## Project Overview

**images2kmz** is a Python tool that creates KMZ files from geotagged photos with embedded thumbnails and links to original images. The project uses a modular package structure for maintainability and extensibility.

## Build & Run Commands

### Setup
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Unix/macOS
# .venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt

# Install optional HEIC support
pip install pillow-heif
```

### Run
```bash
# Basic usage
python main.py /path/to/photos

# With options
python main.py . -o output.kmz -r --convert-heic --thumbnail-size 800 600

# View help
python main.py --help
```

### Testing
```bash
# Currently no test suite exists - add pytest when creating tests
pip install pytest pytest-cov

# Run all tests (future)
pytest

# Run specific test file
pytest tests/test_image_processor.py

# Run specific test function
pytest tests/test_image_processor.py::test_extract_gps_data

# Run with coverage
pytest --cov=images2kmz --cov-report=html
```

### Linting & Formatting
```bash
# Install linting tools (not yet in requirements.txt)
pip install black flake8 mypy ruff

# Format code with black
black images2kmz/ main.py

# Check with flake8
flake8 images2kmz/ --max-line-length=120

# Type checking with mypy
mypy images2kmz/

# Fast linting with ruff
ruff check images2kmz/
```

## Code Style Guidelines

### Imports
- **Order:** Standard library → Third-party → Local imports
- **Grouping:** Separate groups with blank lines
- **Within groups:** `import` statements first, then `from ... import` statements
- **Rationale:** This follows PEP 8 and keeps related imports together for readability

```python
# Standard library - import statements first, then from imports
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# Third-party
from PIL import Image
import simplekml

# Local - use relative imports for sibling modules
from .utils import get_absolute_path
from .image_processor import GPSData
```

### Type Hints
- **Required:** All function signatures must include type hints
- **Use typing module:** Optional, List, Dict, Tuple, Union as needed
- **Return types:** Always specify, use None for procedures
- **Rationale:** Type hints improve code clarity and enable static analysis tools to catch bugs

```python
def extract_gps_data(image_path: str) -> Optional[GPSData]:
    """Extract GPS coordinates from image EXIF data."""
    pass

def process_directory(directory: str, recursive: bool = False) -> List[Dict]:
    """Process all images in a directory."""
    pass
```

### Naming Conventions
- **Functions/Variables:** `snake_case`
- **Classes:** `PascalCase`
- **Constants:** `UPPER_CASE`
- **Private/Internal:** Prefix with single underscore `_internal_method`
- **Protected attributes:** `self._temp_files`, `self._internal_state`
- **Rationale:** Follows PEP 8 conventions; underscore prefix signals internal implementation details

```python
# Good
SUPPORTED_FORMATS = ('.jpg', '.jpeg')

class ImageProcessor:
    def __init__(self):
        self._temp_files: List[str] = []
    
    def process_image(self, file_path: str) -> bool:
        return self._validate_format(file_path)
    
    def _validate_format(self, path: str) -> bool:
        """Internal validation method."""
        pass
```

### Docstrings
- **Style:** Google-style docstrings
- **Required for:** All public functions, classes, and methods
- **Format:** Brief description, then Args/Returns sections
- **Rationale:** Consistent documentation format enables auto-generated docs and helps other developers

```python
def create_thumbnail(image_path: str, max_size: Tuple[int, int] = (800, 600)) -> bytes:
    """
    Create a thumbnail of an image while maintaining aspect ratio.
    
    Args:
        image_path: Path to source image
        max_size: Maximum dimensions (width, height) for thumbnail
        
    Returns:
        Thumbnail image as bytes (JPEG format)
    """
    pass
```

### Error Handling

Choose your error handling strategy based on the operation's criticality:

#### Silent Failures (return None/default)
- **Use for:** Optional operations, batch processing, non-critical paths
- **Example:** Skipping photos without GPS data during batch processing
- **Rationale:** Allows processing to continue; user sees summary report at the end

```python
def extract_gps_data(image_path: str) -> Optional[GPSData]:
    try:
        data = gpsphoto.getGPSData(image_path)
        if data and 'Latitude' in data:
            return GPSData(data['Latitude'], data['Longitude'])
        return None
    except Exception:
        # Silently skip files with errors - they'll appear in "skipped" count
        return None
```

#### Re-raise with Context
- **Use for:** Critical operations where failure invalidates the entire operation
- **Example:** KMZ file save failures
- **Rationale:** Caller needs to know the operation failed; provides context for debugging

```python
def save(self) -> str:
    try:
        self.kml.savekmz(self.output_path)
        return get_absolute_path(self.output_path)
    except Exception as e:
        raise RuntimeError(f"Failed to save KMZ: {e}") from e
```

#### Cleanup in Finally Blocks
- **Always use for:** Temporary files, open file handles, allocated resources
- **Rationale:** Resources must be freed even if errors occur; prevents resource leaks

```python
def save(self) -> str:
    try:
        self.kml.savekmz(self.output_path)
        return get_absolute_path(self.output_path)
    finally:
        # Clean up temporary files even if save fails
        for tmp_file in self._temp_files:
            try:
                os.unlink(tmp_file)
            except Exception:
                pass  # Best effort cleanup
        self._temp_files.clear()
```

### Formatting
- **Line length:** Max 120 characters
- **Indentation:** 4 spaces (no tabs)
- **Quotes:** Single quotes for strings, double for docstrings
- **String formatting:** f-strings preferred over `.format()` or `%`
  - Example: `f"Processed {count} files"` not `"Processed {} files".format(count)`
  - Rationale: More readable, faster, and now standard in modern Python (3.6+)
- **Blank lines:** 2 between top-level definitions, 1 between methods
- **Trailing commas:** Use in multi-line collections for cleaner diffs

## Project-Specific Patterns

### Temporary File Management

When creating temporary files that need to persist until a final operation completes:

1. Create temp file with `delete=False`
2. Track in instance variable (e.g., `self._temp_files: List[str]`)
3. Clean up in `finally` block of the save/commit operation

**Example from core.py:**
```python
class KMZGenerator:
    def __init__(self, output_path: str):
        self._temp_files: List[str] = []
    
    def add_photo(self, photo_path: str, thumbnail_bytes: bytes):
        # Create temp file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp.write(thumbnail_bytes)
            tmp_path = tmp.name
        
        # Track for later cleanup
        self._temp_files.append(tmp_path)
        
        # Use the temp file
        self.kml.addfile(tmp_path)
    
    def save(self) -> str:
        try:
            self.kml.savekmz(self.output_path)
            return get_absolute_path(self.output_path)
        finally:
            # Clean up all temp files
            for tmp_file in self._temp_files:
                try:
                    os.unlink(tmp_file)
                except Exception:
                    pass
            self._temp_files.clear()
```

**Rationale:** simplekml needs files to exist on disk when creating the KMZ archive, but we must clean them up afterward to avoid leaving temp files in system directories.

### Optional Dependencies

(Section removed: HEIC support is now mandatory and handled via `pillow-heif` in core requirements.)

### CLI Exit Codes

Command-line functions should return int exit codes:
- `0`: Success
- `1`: General error (file not found, processing failed)
- Non-zero: Error conditions

```python
def run(args: Optional[list] = None) -> int:
    try:
        # ... processing logic
        return 0  # Success
    except FileNotFoundError:
        print(f"Error: Directory not found")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
```

**Rationale:** Shell scripts and automation tools can detect failures via the exit code (`$?` in bash), enabling proper error handling in pipelines.

### EXIF Orientation Handling

Always use `ImageOps.exif_transpose()` when opening images for processing:

```python
from PIL import Image, ImageOps

def create_thumbnail(image_path: str, max_size: Tuple[int, int]) -> bytes:
    with Image.open(image_path) as img:
        # Handle EXIF orientation
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass  # If no EXIF data, continue with original
        
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        # ... save thumbnail
```

**Rationale:** Many cameras store image rotation in EXIF metadata rather than physically rotating pixels. Without `exif_transpose()`, thumbnails may appear rotated incorrectly. The try/except handles images without EXIF data gracefully.

### Cross-Platform Path Handling

- Use `os.path` functions or `pathlib.Path` objects
- Never hardcode `/` or `\` in path strings
- Use `os.path.join()` or `/` operator with Path objects

```python
# Good
import os
from pathlib import Path

path = os.path.join(directory, filename)
path = Path(directory) / filename

# Bad - hardcoded separators break on Windows
path = directory + "/" + filename
```

**Rationale:** Windows uses backslashes (`\`), Unix uses forward slashes (`/`). Using path manipulation functions ensures code works on all platforms without modification.

## Module Structure

### Package Organization
```
images2kmz/
├── __init__.py          # Public API exports
├── cli.py               # Command-line interface
├── core.py              # Core business logic (KMZGenerator)
├── image_processor.py   # Image operations (GPS, thumbnails)
├── heic_handler.py      # Format conversion
└── utils.py             # Utility functions
```

### Module Responsibilities
- **cli.py:** Argument parsing, user interaction, orchestration
- **core.py:** KMZ file generation, KML structure creation
- **image_processor.py:** EXIF reading, thumbnail creation, file discovery
- **heic_handler.py:** HEIC detection and conversion to JPEG
- **utils.py:** Path handling, formatting helpers (pure functions, no state)

**Rationale:** Clear separation of concerns makes the codebase easier to understand, test, and extend. Each module has a single, well-defined responsibility.

## Common Development Tasks

### Adding a New Feature
1. Determine which module it belongs in (or create new module if it's a distinct concern)
2. Add type-hinted functions with Google-style docstrings
3. Update `__init__.py` exports if it's part of the public API
4. Add CLI arguments in `cli.py::create_parser()` if user-facing
5. Update README.md with usage examples
6. Add tests covering both success and failure cases

### Adding a New Image Format
1. Update `SUPPORTED_FORMATS` constant in `image_processor.py`
2. Add format detection logic in `is_supported_format()`
3. Handle format-specific EXIF quirks in `extract_gps_data()`
4. Test with sample images in the new format
5. Update documentation (README.md and this file)

### Modifying CLI Behavior
1. Update argument parser in `cli.py::create_parser()`
2. Modify orchestration logic in `cli.py::run()`
3. Update help text and epilog to reflect new behavior
4. Update README.md examples
5. Ensure backward compatibility or document breaking changes

## Testing Guidelines

### Test Structure
```
tests/
├── __init__.py
├── test_image_processor.py
├── test_core.py
├── test_heic_handler.py
├── test_utils.py
└── fixtures/
    └── sample_images/
```

### Test Conventions
- **Framework:** Use pytest (preferred over unittest for cleaner syntax and better fixtures)
- **Mock external dependencies** to make tests fast and deterministic:
  - `gpsphoto.getGPSData()` - return fake GPS coordinates with known values
  - File I/O - use pytest's `tmp_path` fixture for temporary directories
  - `PIL.Image.open()` - use test fixture images with known properties
- **Provide fixture images** with:
  - Known GPS coordinates for validation (e.g., 48.858844, 2.294351 - Eiffel Tower)
  - Various EXIF orientations (test rotation handling)
  - Missing GPS data (test graceful failure)
  - Different formats (JPEG baseline, progressive)
- **Test both success and failure cases** for each function
- **Aim for >80% coverage** on core modules (image_processor, core, utils)
- **Rationale:** Tests give confidence when refactoring; mocking prevents tests from being slow or dependent on external services

### Quick Validation

Before committing code changes, validate with actual sample images:

```bash
# Process sample images in current directory
python main.py . -o test.kmz

# Verify KMZ was created with expected size
ls -lh test.kmz

# Inspect contents
unzip -l test.kmz

# Clean up
rm test.kmz
```

**Rationale:** Quick integration test catches basic issues before running full test suite. Real images often expose edge cases that mocked tests miss.

## Debugging Tips

### Inspecting KMZ Files

KMZ files are ZIP archives containing KML and embedded images. To debug issues:

```bash
# Extract KMZ contents to a directory
unzip output.kmz -d debug_output/

# View KML structure
cat debug_output/doc.kml | head -100

# Check embedded images exist and have reasonable sizes
ls -lh debug_output/files/

# Validate KML syntax (requires xmllint)
xmllint --noout debug_output/doc.kml && echo "Valid KML" || echo "Invalid KML"
```

### Common Issues

**Photos not appearing in KMZ:**
- Check GPS data exists: `python -c "from GPSPhoto import gpsphoto; print(gpsphoto.getGPSData('photo.jpg'))"`
- Verify file format: Only .jpg/.jpeg files are processed (unless HEIC converted first)
- Check file permissions: Ensure photos are readable

**Thumbnails appear rotated:**
- Ensure `ImageOps.exif_transpose()` is called in `create_thumbnail()` before resizing
- Some cameras store rotation in EXIF orientation tag; without handling this, images appear sideways

**"File not found" errors with temp files:**
- Check `_temp_files` cleanup isn't happening too early
- Ensure `finally` block in `save()` runs after KMZ creation, not after each `add_photo()`
- Verify temp files have `delete=False` when created

**Memory issues with large directories:**
- Current implementation processes one image at a time (memory efficient)
- If adding batch processing, ensure thumbnails aren't all loaded into memory simultaneously
- Use generators or process in chunks of ~100 images

**HEIC conversion fails:**
- Check if `pillow-heif` is installed: `pip list | grep pillow-heif`
- Some HEIC variants (10-bit color) may not be supported

### Validation Commands

```bash
# Check if a specific image has GPS data
python -c "from images2kmz import extract_gps_data; print(extract_gps_data('IMG_1234.jpg'))"

# Test thumbnail generation on a single image
python -c "from images2kmz import create_thumbnail; data = create_thumbnail('IMG_1234.jpg'); print(f'{len(data)} bytes')"

# Count images with GPS data in a directory
python -c "from images2kmz import get_image_files, extract_gps_data; files = get_image_files('.'); gps_count = sum(1 for f in files if extract_gps_data(f)); print(f'{gps_count}/{len(files)} images have GPS')"

# Verify KMZ opens in Google Earth (platform-specific)
open output.kmz           # macOS
xdg-open output.kmz       # Linux
start output.kmz          # Windows
```

**Rationale:** These commands help diagnose issues at each stage of the processing pipeline, making it easier to isolate where failures occur.

## Additional Notes

- **Python Version:** Requires Python 3.7+ (uses type hints, f-strings, and dict ordering guarantees)
- **Dependencies:** Keep minimal to reduce installation size and potential conflicts; avoid heavy frameworks
- **Backward Compatibility:** Maintain existing CLI interface; new options are fine, but don't change behavior of existing flags
- **Performance:** Process images one at a time (memory efficient); avoid loading all images before processing
- **Cross-platform:** Use `os.path` and `pathlib` for paths; test on Windows, macOS, and Linux if possible
- **Modularity:** Each module should be importable and usable independently (enables using as a library, not just CLI)
