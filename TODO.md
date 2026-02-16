# Project Improvements TODO List

Generated from code review on 2026-02-15

---

## Critical Issues (Must Fix)

### 1. Double Cleanup Bug in KMZGenerator.save()
**File:** `src/images2kmz/core.py` (lines 191-217)

The `save()` method calls `cleanup()` inside the `try` block (line 217), but also has a `finally` block that unconditionally calls `cleanup()`. This will cause errors because:
- If save succeeds, temp directory is already cleaned up
- If save fails, the context manager's `__exit__` will also try to cleanup

**Fix:** Remove the `finally` block - the context manager handles cleanup

---

### 2. CSV Export Empty Return Type Inconsistency
**File:** `src/images2kmz/csv_exporter.py` (lines 146-148)

`CSVExporter.export()` returns `""` (empty string) when there's no data, while other similar methods return `None`. This is inconsistent.

**Fix:** Return `None` instead of `""` for consistency

---

## Important Issues (Should Fix)

### 3. Code Duplication: File Discovery Functions
**Files:** `image_processor.py` and `heic_handler.py`

`get_image_files()` and `find_heic_files()` have identical logic patterns. Extract to shared utility.

**Suggested implementation in `utils.py`:**
```python
def find_files_by_extension(
    directory: str | Path,
    extensions: tuple[str, ...],
    recursive: bool = False
) -> list[str]:
    """Find all files with given extensions in a directory."""
```

---

### 4. Hardcoded Configuration Values

#### 4a. KML Icon URLs
**File:** `core.py` lines 124, 129
```python
pnt.style.iconstyle.icon.href = 'http://earth.google.com/images/kml-icons/track-directional/track-0.png'
```

**Fix:** Create module constants:
```python
DEFAULT_ICON_WITH_BEARING = 'http://earth.google.com/images/kml-icons/track-directional/track-0.png'
DEFAULT_ICON_NO_BEARING = 'http://earth.google.com/images/kml-icons/track-directional/track-none.png'
```

#### 4b. CSV Starting Point Number
**File:** `csv_exporter.py` line 26
```python
starting_point_number: int = 9001,
```

**Fix:** Document this as a CLI option or config value

---

### 5. Inefficient Coordinate Transformer Creation
**File:** `csv_exporter.py` lines 104-108

`latlon_to_utm()` creates a new `Transformer` on every call instead of caching. This is inefficient for processing many images.

**Fix:** Cache transformers by UTM zone:
```python
def _get_utm_transformer(self, utm_zone: str) -> Transformer:
    if not hasattr(self, '_utm_transformers'):
        self._utm_transformers = {}
    if utm_zone not in self._utm_transformers:
        self._utm_transformers[utm_zone] = Transformer.from_crs(...)
    return self._utm_transformers[utm_zone]
```

---

## Suggestions (Nice to Have)

### 6. Standardize Path Type Hints

| Function | Current | Suggested |
|----------|---------|-----------|
| `KMZGenerator.__init__` | `str` | `str \| Path` |
| `ImageProcessor.process_directory` | `str` | `str \| Path` |
| `add_photo` | `str` | `str \| Path` |

---

### 7. Add Defensive GPS Data Validation
**File:** `cli.py` lines 377-385

Add a safety check when adding photos to KMZ:
```python
if img_data.get('gps') is None:
    logger.warning(f"Skipping {img_data['path']}: missing GPS data")
    continue
```

---

### 8. Module-Level Console Instance
**File:** `heic_handler.py` line 12

`console = Console()` is created at module import time. Consider passing `Console` as a parameter for better testability.

---

### 9. Missing Docstrings
- `_get_transformer()` in `csv_exporter.py`
- `_process_single_image()` in `image_processor.py` (add proper docstring)

---

### 10. Extract HTML Templates
**File:** `core.py` lines 132-170

The KML description HTML is hardcoded in `add_photo()`. Consider extracting to a template function for easier maintenance.

---

## Already Completed (from previous TODO)

- ✅ Parallelize Image Processing (using ProcessPoolExecutor)
- ✅ Improve Resource Management (using tempfile.TemporaryDirectory)
- ✅ Add Verbose Logging (--verbose flag implemented)
