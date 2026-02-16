# Plan: Condense AGENTS.md

## Goal
Reduce AGENTS.md from 541 lines to ~150 lines while keeping essential information for agentic coding assistants.

## Proposed Content

```markdown
# AGENTS.md - Developer Guide for images2kmz

Guidelines for agentic coding assistants working in this repository.

## Project Overview

**images2kmz** is a Python CLI tool that creates KMZ files from geotagged photos with thumbnails. Architecture: modular package with separate concerns (CLI, core, image processing, utilities).

## Commands

### Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest black flake8 mypy  # dev tools
```

### Run
```bash
python main.py /path/to/photos -o output.kmz -r --thumbnail-size 800 600
```

### Testing
```bash
pytest                          # run all tests
pytest tests/test_image_processor.py       # single test file
pytest tests/test_image_processor.py::test_extract_gps_data  # single test
pytest -v                      # verbose
pytest --cov=images2kmz        # with coverage
```

### Linting
```bash
black images2kmz/ main.py
flake8 images2kmz/ --max-line-length=120
mypy images2kmz/
ruff check images2kmz/
```

## Code Style

### Imports
- Order: Standard library → Third-party → Local (separate with blank lines)
- Within groups: `import` first, then `from ... import`
- Example:
```python
import os
from pathlib import Path
from typing import Optional

from PIL import Image
import simplekml

from .utils import get_absolute_path
```

### Types
- Required: All function signatures must have type hints
- Use: `Optional`, `List`, `Dict`, `Tuple`, `Union` from typing module
- Example:
```python
def extract_gps_data(image_path: str) -> Optional[GPSData]:
    pass
def process_directory(directory: str) -> List[Dict]:
    pass
```

### Naming
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_CASE`
- Private methods: `_prefix_with_underscore`

### Docstrings
- Google-style for public functions/classes
- Include Args and Returns sections

```python
def create_thumbnail(image_path: str, max_size: Tuple[int, int]) -> bytes:
    """Create thumbnail while maintaining aspect ratio.
    
    Args:
        image_path: Path to source image
        max_size: Maximum dimensions (width, height)
        
    Returns:
        Thumbnail as JPEG bytes
    """
```

### Error Handling
1. **Silent failures** (return None): Optional operations like extracting GPS from batch
2. **Re-raise with context**: Critical operations like KMZ save
3. **Cleanup in finally**: Always clean up temp files

```python
# Silent failure
def extract_gps_data(path: str) -> Optional[GPSData]:
    try:
        return _extract(path)
    except Exception:
        return None

# Cleanup pattern
for tmp in self._temp_files:
    try: os.unlink(tmp)
    except Exception: pass
```

### Formatting
- Line length: 120 max
- Indentation: 4 spaces
- Quotes: single for strings, double for docstrings
- F-strings preferred: `f"Processed {count} files"`
- Trailing commas in multi-line collections

## Key Patterns

### Temp File Management
```python
# Create with delete=False, track, cleanup in finally
with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
    tmp.write(data)
    self._temp_files.append(tmp.name)
```

### EXIF Orientation
Always use `ImageOps.exif_transpose()` before processing:
```python
from PIL import ImageOps
img = ImageOps.exif_transpose(img)
```

### Paths
Use `pathlib.Path` or `os.path`, never hardcode `/` or `\`:
```python
path = Path(directory) / filename
```

## Module Structure

```
images2kmz/
├── __init__.py          # Public API exports
├── cli.py               # CLI entry point
├── core.py              # KMZ generation
├── image_processor.py   # EXIF, thumbnails
└── utils.py             # Pure utility functions
```

## Exit Codes

- `0`: Success
- `1`: Error (file not found, processing failed)

## Testing Guidelines

- Mock external deps: `gpsphoto.getGPSData()`, `PIL.Image.open()`
- Use pytest fixtures with real images having known GPS coords
- Target >80% coverage on core modules
- Test both success and failure paths

## Debugging

```bash
# Inspect KMZ (it's a ZIP)
unzip output.kmz -d debug/
cat debug/doc.kml

# Check GPS data
python -c "from GPSPhoto import gpsphoto; print(gpsphoto.getGPSData('photo.jpg'))"
```

## Dependencies

- Core: `Pillow`, `simplekml`, `GPSPhoto`, `pillow-heif`
- Dev: `pytest`, `black`, `flake8`, `mypy`, `ruff`
```

## Line Count Target
The condensed version is approximately 150 lines compared to the current 541 lines.

## Files to Modify
- `/Users/hugochisholm/projects/images2kmz-gv/AGENTS.md`

## Verification
After update, verify:
1. File is ~150 lines (not 541)
2. All essential commands are present (pytest with single test option)
3. Code style guidelines are clear
4. No Cursor/Copilot rules to include (none exist in repo)
