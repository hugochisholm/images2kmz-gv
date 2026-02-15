# images2kmz

Python CLI tool for creating KMZ (Google Earth) files from geotagged photos.

## Features

- Create KMZ files from geotagged photos
- Support for multiple image formats (JPEG, HEIC, PNG)
- Automatic GPS coordinate extraction
- Thumbnail generation for Google Earth
- Progress indicators with rich console output

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

### Interactive Mode

Run without arguments for an interactive experience:

```bash
python -m images2kmz
```

You'll be prompted to:
1. Enter a directory path containing images
2. Optionally create the directory if it doesn't exist
3. The generated KMZ file will be saved in the same directory

**Supports:** relative paths (`./photos`), absolute paths (`/Users/username/photos`), home directory (`~/photos`), and Windows paths (`C:\Users\username\Pictures`)

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

# Auto-convert HEIC files
images2kmz /path/to/photos --convert-heic -o output.kmz

# Custom thumbnail size
images2kmz /path/to/photos --thumbnail-size 1024 768 -o output.kmz

# Show help
images2kmz --help
```

#### Command-Line Options

- `input_dir`: Directory containing photos (optional; will prompt if not provided)
- `-o, --output`: Output KMZ file path (default: `{input_dir}/photos.kmz`)
- `-r, --recursive`: Recursively search subdirectories
- `--thumbnail-size WIDTH HEIGHT`: Maximum thumbnail dimensions (default: 800 600)
- `--convert-heic`: Automatically convert HEIC files without prompting
- `--version`: Show version information

#### Examples

Process photos in specified directory:
```bash
images2kmz ~/Photos
# Output: ~/Photos/photos.kmz
```

Process photos recursively:
```bash
images2kmz ~/Photos -r
# Output: ~/Photos/photos.kmz
```

Custom output location:
```bash
images2kmz ~/Photos -o ~/Desktop/vacation.kmz
# Output: ~/Desktop/vacation.kmz
```

Auto-convert HEIC files:
```bash
images2kmz ~/Photos -r --convert-heic
```

Custom thumbnail size:
```bash
images2kmz ~/Photos --thumbnail-size 1024 768
```

### As a Python Module

You can also import and use images2kmz in your own Python scripts:

```python
from images2kmz import ImageProcessor, KMZGenerator

# Process images
processor = ImageProcessor(thumbnail_size=(800, 600))
images = processor.process_directory('/path/to/photos', recursive=True)

# Get statistics
stats = processor.get_stats()
print(f"Processed {stats['processed']} photos")
print(f"Skipped {stats['skipped_no_gps']} photos without GPS")

# Generate KMZ
kmz = KMZGenerator('output.kmz')
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
4. **Thumbnail Creation**: Generates resized thumbnails (800x600 max, preserving aspect ratio)
5. **KMZ Generation**: Creates a KMZ file with:
   - Placemarks at each photo's GPS location
   - Photo filename as the placemark name
   - Embedded thumbnail in the description balloon
   - Hyperlink to open the original photo

## Output

The generated KMZ file can be opened in:
- Google Earth
- Google Maps (via "My Maps")
- Other KML/KMZ compatible applications

When you click on a placemark:
- The thumbnail image is displayed
- A link to the original photo allows you to open the full-resolution image

## Project Structure

The project uses a modern src layout:

```
images2kmz/
├── src/
│   └── images2kmz/        # Source code
│       ├── __init__.py    # Package exports
│       ├── __main__.py    # Entry point for python -m
│       ├── cli.py         # Command-line interface
│       ├── core.py        # KMZ generation engine
│       ├── image_processor.py   # Image handling (thumbnails, EXIF)
│       ├── heic_handler.py      # HEIC detection and conversion
│       ├── progress.py          # Progress bar utilities
│       └── utils.py             # Utility functions
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
- textual >= 0.30.0
- piexif >= 1.1.3
- pillow-heif >= 0.10.0

## Limitations

- Only JPEG and HEIC files are processed
- Photos without GPS EXIF data are skipped
- Hyperlinks to original photos use absolute file paths (local filesystem only)

## Future Enhancements

The modular design makes it easy to add:
- Photo filtering by date range
- Custom pin icons based on metadata
- Clustering of nearby photos
- Export to other formats (GeoJSON, GPX)
- GUI wrapper
- Batch processing of multiple directories

## License

MIT License - Feel free to use and modify as needed.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.
