# Project Improvements TODO List

## High Priority

### 1. Parallelize Image Processing
- **Task:** Update `process_directory` to use `concurrent.futures.ProcessPoolExecutor`.
- **Rationale:** The current implementation processes images sequentially. Parallelizing this will significantly reduce runtime for large datasets by utilizing multiple CPU cores.

### 2. Improve Resource Management (Temp Files)
- **Task:** Replace manual list-based temp file tracking in `KMZGenerator` with `tempfile.TemporaryDirectory`.
- **Rationale:** If the script crashes, temp files might be left behind. Using a context manager ensures proper cleanup automatically.

## Medium Priority

### 3. Refactor KML Description HTML
- **Task:** Move hardcoded HTML strings from `core.py` to a dedicated template function or constant.
- **Rationale:** Hardcoded HTML mixed with logic makes the code harder to read and maintain. Separating the view logic allows for easier design updates.

### 4. Extract Hardcoded Strings
- **Task:** Move business logic strings like "GeoVerra, Nav Photo - " to constants or configuration.
- **Rationale:** Hardcoding specific business strings limits the tool's reusability. Making them configurable improves maintainability.

### 5. Add Verbose Logging
- **Task:** Add a `--verbose` flag and implement proper logging for skipped/error files.
- **Rationale:** Silent failures make debugging difficult. Users need to know *why* a file was skipped (e.g., corrupt EXIF) to fix the issue.
