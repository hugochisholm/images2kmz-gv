# images2kmz

A Python tool to create KMZ files from geotagged photos with embedded thumbnails and links to original images.

## Features

- **GPS Extraction**: Automatically extracts GPS coordinates from photo EXIF data
- **Thumbnail Generation**: Creates 800x600 thumbnails (maintaining aspect ratio) embedded in KMZ
- **Original Links**: Includes hyperlinks to original photos on your filesystem
- **HEIC Support**: Optional conversion of HEIC/HEIF files to JPEG
- **Recursive Scanning**: Can search subdirectories for photos
- **Summary Reports**: Shows statistics about processed photos
- **Modular Design**: Can be used as a Python module or command-line tool

## Installation

1. Clone or download this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

### Optional: HEIC Support

To enable HEIC/HEIF conversion, install the additional dependency:

```bash
pip install pillow-heif
```

Or uncomment the `pillow-heif` line in `requirements.txt` and reinstall.

## Usage

### Command Line

Basic usage:

```bash
python main.py /path/to/photos
```

With options:

```bash
python main.py /path/to/photos -o output.kmz -r --convert-heic
```

#### Command-Line Options

- `input_dir`: Directory containing photos (required)
- `-o, --output`: Output KMZ file path (default: photos.kmz)
- `-r, --recursive`: Recursively search subdirectories
- `--thumbnail-size WIDTH HEIGHT`: Maximum thumbnail dimensions (default: 800 600)
- `--convert-heic`: Automatically convert HEIC files without prompting
- `--version`: Show version information

#### Examples

Process photos in current directory:
```bash
python main.py .
```

Process photos recursively with custom output:
```bash
python main.py ~/Photos/Vacation -o vacation.kmz -r
```

Auto-convert HEIC files:
```bash
python main.py ~/Photos -r --convert-heic
```

Custom thumbnail size:
```bash
python main.py ~/Photos --thumbnail-size 800 600
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

## Requirements

- Python 3.7+
- GPSPhoto >= 2.2.3
- simplekml >= 1.3.6
- Pillow >= 12.0.0
- textual >= 0.30.0 (for TUI interface)
- pillow-heif >= 0.10.0 (optional, for HEIC support)

## Project Structure

```
images2kmz/
├── images2kmz/              # Main package
│   ├── __init__.py          # Package exports
│   ├── cli.py               # Command-line interface
│   ├── core.py              # KMZ generation engine
│   ├── image_processor.py   # Image handling (thumbnails, EXIF)
│   ├── heic_handler.py      # HEIC detection and conversion
│   ├── utils.py             # Utility functions
│   └── tui_app.py           # Terminal UI application
├── main.py                  # Entry point for CLI
├── tui_main.py              # Entry point for TUI
├── requirements.txt         # Python dependencies
├── README.md                # This file
└── .gitignore               # Git ignore patterns
```

## Limitations

- Only JPEG files are processed (HEIC files must be converted first)
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
