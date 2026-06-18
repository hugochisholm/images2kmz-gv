# images2kmz

Python CLI tool for creating KMZ (Google Earth) files from geotagged photos.

## Features

- Create KMZ files from geotagged photos
- Support for multiple image formats (JPEG, HEIC, PNG)
- Automatic GPS coordinate extraction
- Thumbnail generation for Google Earth
- Compass bearing icon rotation based on photo direction
- Bundled pin icons embedded in every KMZ — no network connection required to view placemarks
- GeoVerra-branded TUI launches by default with no arguments; includes a built-in filesystem browser and real-time progress bars
- Progress bars and summaries are preserved in the TUI log for auditability
- Always displays data integrity panels (missing location/direction) for transparency
- Export to CSV with UTM coordinates for AutoCAD (includes custom date-based point numbering, azimuth info, and full photo paths)
- Configurable placemark info fields (direction, location, photo path, description)
- Preset modes for common configurations (full, minimal, client)
- ExtendedData support for structured info display in KML balloons
- GeoVerra network path remapping: `\\*fs\GV-Volume\Projects\` paths are rewritten to `file:///V:/…` for cross-office portability

## Installation

### Prerequisites

- Python 3.10+
- Virtual environment (located at `./.venv/`)

### Setup

```bash
# Activate the virtual environment
source ./.venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate  # On Windows

# Install in development mode
pip install -e .

# Install dev dependencies (optional)
pip install -r requirements-dev.txt
```

## Usage

### Interactive Mode (TUI)

Running with no arguments launches the GeoVerra-branded TUI directly:

```bash
python -m images2kmz
# or
images2kmz
```

The TUI provides:
- A built-in filesystem browser for selecting the input directory
- Dropdown menus for thumbnail size (with resolution labels) and placemark preset (with field summaries)
- Real-time progress bars and a persistent log for auditability
- Output files saved to `{input_dir}/images2kmz/` by default

Pass `--tui` explicitly to the same effect if you prefer.

### Command Line

Basic usage:

```bash
images2kmz /path/to/photos
```

With options:

```bash
# Specify output file
images2kmz /path/to/photos -o output.kmz

# Process recursively
images2kmz /path/to/photos --recursive -o output.kmz

# Custom thumbnail size
images2kmz /path/to/photos --thumbnail-size medium -o output.kmz

# Verbose output (shows processing progress)
images2kmz /path/to/photos -v

# Enable debug log file (saved to output or input directory)
images2kmz /path/to/photos --log-file

# Export photo coordinates to CSV with UTM coordinates
images2kmz /path/to/photos --csv

# Export CSV with custom coordinate system (default: NAD83/EPSG:4269)
images2kmz /path/to/photos --csv --coordinate-system EPSG:4326

# Control placemark info card fields
images2kmz /path/to/photos --placemark-fields=location,description

# Use preset for placemark fields (full/minimal/client/none)
images2kmz /path/to/photos --preset=client

# Hide photo path link (for external sharing - backward compatible)
images2kmz /path/to/photos --no-photo-path

# Limit the number of images per KMZ output file
images2kmz /path/to/photos --max-images=50

# Show help
images2kmz --help
```

#### Command-Line Options

- `input_dir`: Directory containing photos (optional; omitting it launches the TUI)
- `-o, --output`: Output KMZ file path (default: `{input_dir}/images2kmz/photos.kmz`)
- `-r, --recursive`: Recursively search subdirectories
- `--thumbnail-size PRESET`: Thumbnail size preset ('small', 'medium', or 'large', default: medium)
- `--max-images N`: Maximum number of images per KMZ output file (default: 100, 0 for unlimited)
- `--tui`: Explicitly launch the TUI (same as running with no arguments)
- `-v, --verbose`: Enable verbose console output with timestamped log file
- `-l, --log-file`: Enable debug log file (default: `{input_dir}/images2kmz/images2kmz.log`)
- `--csv`: Export photo coordinates to CSV file (default: `{input_dir}/images2kmz/photo_points.csv`)
- `--coordinate-system EPSG`: Override default coordinate system (default: EPSG:4269 NAD83)
- `--placemark-fields FIELDS`: Comma-separated fields to include in placemark info (direction,location,photo_path,description,all)
- `--preset PRESET`: Use preset configuration (full/minimal/client/none)
- `--no-photo-path`: Don't include photo path link in placemark (for external sharing)
- `--version`: Show version information

#### Examples

Process photos in specified directory:
```bash
images2kmz ~/Photos
# Output: ~/Photos/images2kmz/photos.kmz
```
Process photos recursively:
```bash
images2kmz ~/Photos -r
# Output: ~/Photos/images2kmz/photos.kmz
```

Custom output location:
```bash
images2kmz ~/Photos -o ~/Desktop/vacation.kmz
# Output: ~/Desktop/vacation.kmz
```

Custom thumbnail size:
```bash
images2kmz ~/Photos --thumbnail-size small
```

#### CSV Export Format

When exporting to CSV using the `--csv` flag, the output file `photo_points.csv` includes the following 6 columns without a header row:
1. **Point Number:** Generated based on the photo's EXIF capture date (or file modification date) and a sequence number starting at 9001 (e.g., `YYMMDD9001`).
2. **Northing:** The UTM northing coordinate (to 4 decimal places).
3. **Easting:** The UTM easting coordinate (to 4 decimal places).
4. **Elevation:** The GPS altitude extracted from EXIF (0.0000 if not available).
5. **Description:** Contains the camera azimuth/bearing and photo description, e.g., `PHOTO(145) Site Location B` or just `PHOTO Site Location B` if azimuth is unavailable.
6. **File Path:** The absolute file path to the original photo (same as the "Open Original Photo" link in the KMZ).

#### Controlling Placemark Info Fields

```bash
# Show only location and description (no direction or photo path)
images2kmz ~/Photos --placemark-fields=location,description

# Use client preset (no photo path - good for external sharing)
images2kmz ~/Photos --preset=client

# Minimal mode - thumbnail only, no info fields
images2kmz ~/Photos --preset=minimal
```

### As a Python Module

You can also import and use images2kmz in your own Python scripts:

```python
from images2kmz import ImageProcessor, KMZGenerator, PlacemarkConfig

# Process images (parallel processing with up to 8 workers by default)
processor = ImageProcessor(thumbnail_size='medium', max_workers=4)
images = processor.process_directory('/path/to/photos', recursive=True)

# Get statistics
stats = processor.get_stats()
print(f"Processed {stats['processed']} photos")
print(f"Skipped {stats['skipped_no_gps']} photos without GPS")

# Configure placemark fields
config = PlacemarkConfig.from_preset('client')  # No photo path for external sharing
# Or: config = PlacemarkConfig(show_direction=False, show_location=True)

# Generate KMZ (using context manager for automatic cleanup)
with KMZGenerator('output.kmz', thumbnail_size='medium', placemark_config=config) as kmz:
    for img in images:
        kmz.add_photo(
            photo_path=img['path'],
            gps_data=img['gps'],
            thumbnail_bytes=img['thumbnail'],
            name=img['filename']
        )
    kmz.save()
```

## How It Works

1. **Scanning**: The tool scans the specified directory for JPEG images
2. **HEIC Handling**: If HEIC files are found, optionally converts them to JPEG
3. **GPS Extraction**: Reads EXIF data from each image to extract GPS coordinates
4. **Compass Bearing**: Extracts photo direction from EXIF GPS data
5. **Thumbnail Creation**: Generates resized thumbnails (800x600 max, preserving aspect ratio)
6. **KMZ Generation**: Creates a KMZ file with:
   - Placemarks at each photo's GPS location
   - Photo filename as the placemark name
   - Directional icon rotated to match photo bearing (if available)
   - Pin icons bundled inside the KMZ archive — no internet needed to display them
   - Embedded thumbnail in the description balloon
   - ExtendedData with structured info (direction, location, photo path, description)
   - Hyperlink to open the original photo (configurable)
   - GeoVerra network paths (`\\*fs\GV-Volume\Projects\`) rewritten to `file:///V:/…` for consistent cross-office behaviour

## Output

The generated KMZ file can be opened in:
- Google Earth
- Google Maps (via "My Maps")
- Other KML/KMZ compatible applications

When you click on a placemark:
- The thumbnail image is displayed
- A structured info table shows direction, location, and photo path (based on configuration)
- A link to the original photo allows you to open the full-resolution image (if enabled)

## Project Structure

The project uses a modern src layout:

```
images2kmz/
├── src/
│   └── images2kmz/        # Source code
│       ├── icons/                     # Bundled pin icons (embedded in every KMZ)
│       │   ├── track-0.png            # Directional arrow icon
│       │   └── track-none.png         # Non-directional dot icon
│       ├── __init__.py    # Package exports
│       ├── __main__.py    # Entry point for python -m
│       ├── cli.py         # Command-line interface
│       ├── core.py        # KMZ generation engine
│       ├── image_processor.py   # Image handling (thumbnails, EXIF)
│       ├── csv_exporter.py      # CSV export with UTM coordinates
│       ├── heic_handler.py      # HEIC detection and conversion
│       ├── placemark_config.py   # Placemark field configuration
│       ├── placemark_html_builder.py  # HTML/ExtendedData generation
│       ├── logging_config.py    # Logging configuration
│       ├── progress.py          # Progress bar utilities
│       ├── tui.py               # GeoVerra-branded TUI with directory picker
│       ├── ui_handler.py        # Abstract UI interface for progress and output
│       └── utils.py             # Utility functions (paths, file URIs)
├── tests/                 # Test suite
├── setup.py               # Package configuration
├── README.md
└── requirements*.txt
```

## Development

### Running Tests

**Note: All commands must be run through the virtual environment at `./.venv/`:**

```bash
# Activate the virtual environment
source ./.venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate  # On Windows

# Run all tests
pytest

# Run with coverage
pytest --cov=images2kmz

# Run specific test file
pytest tests/test_core.py
```

### Code Style

This project follows modern Python 3.10+ standards:

- Type hints using `X | None` instead of `Optional[X]`
- `pathlib.Path` for all file operations
- `from __future__ import annotations` for forward references
- Rich console for styled output

See [AGENTS.md](AGENTS.md) for detailed coding standards and guidelines.

## Requirements

- Python 3.10+
- GPSPhoto >= 2.2.3
- Pillow >= 12.0.0
- simplekml >= 1.3.6
- rich >= 13.0.0
- pillow-heif >= 0.10.0
- pyproj >= 3.6.0
- exifread

## Limitations

- Only JPEG and HEIC files are processed
- Photos without GPS EXIF data are skipped
- Hyperlinks to original photos use absolute file paths (local filesystem only)

## Future Enhancements

The modular design makes it easy to add:
- Photo filtering by date range
- Custom pin icons based on metadata
- Clustering of nearby photos
- Export to other formats (GeoJSON, GPX) - CSV export now available
- GUI wrapper
- Batch processing of multiple directories

## License

MIT License - Feel free to use and modify as needed.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.
