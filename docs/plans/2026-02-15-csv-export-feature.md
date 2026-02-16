# CSV Export Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add optional CSV export of processed photos with UTM coordinates for AutoCAD import. CSV format: Point_number, Northing, Easting, Elevation, description. Point numbers use YYMMDD9001 format with sequential numbering starting at 9001.

**Architecture:** Create new `csv_exporter.py` module with UTM conversion via pyproj. Add CLI flags `--csv` (optional output) and `--coordinate-system` (default NAD83). Integrate after image processing phase.

**Tech Stack:** Python, pyproj (for UTM conversion), existing CSV module

**Dependencies to add:** pyproj>=3.6.0

---

## Task 1: Add pyproj to requirements

**Files:**
- Modify: `requirements.txt`
- Modify: `requirements-dev.txt` (if exists)

**Step 1: Add pyproj to requirements.txt**

```python
# Add to requirements.txt after pillow-heif
pyproj>=3.6.0
```

**Step 2: Commit**

```bash
git add requirements.txt
git commit -m "feat: add pyproj for UTM coordinate conversion"
```

---

## Task 2: Create csv_exporter module

**Files:**
- Create: `src/images2kmz/csv_exporter.py`

**Step 1: Write the module**

```python
"""CSV export functionality for survey data with UTM coordinates."""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path

from pyproj import Transformer

from .image_processor import GPSData

logger = logging.getLogger(__name__)

# Default coordinate system
DEFAULT_COORDINATE_SYSTEM = "EPSG:4269"  # NAD83


class CSVExporter:
    """Export processed photos to CSV format for AutoCAD import."""

    def __init__(
        self,
        coordinate_system: str = DEFAULT_COORDINATE_SYSTEM,
        starting_point_number: int = 9001,
    ):
        """
        Initialize CSV exporter.

        Args:
            coordinate_system: EPSG code or proj4 string for coordinate transformation.
                              Default is NAD83 (EPSG:4269).
            starting_point_number: Initial point number for sequential numbering (default: 9001)
        """
        self.coordinate_system = coordinate_system
        self.starting_point_number = starting_point_number
        self._transformer: Transformer | None = None

    def _get_transformer(self) -> Transformer:
        """Get or create the coordinate transformer."""
        if self._transformer is None:
            # UTM zones are north-oriented, so we transform from source CRS to UTM
            # We'll determine the UTM zone automatically based on longitude
            self._transformer = Transformer.from_crs(
                self.coordinate_system,
                "EPSG:4326",  # WGS84 - get lat/lon first
                always_xy=True,
            )
        return self._transformer

    def _get_utm_zone(self, longitude: float) -> str:
        """
        Determine UTM zone from longitude.

        Args:
            longitude: Longitude in degrees

        Returns:
            EPSG code for the appropriate UTM zone
        """
        # UTM zones are 6 degrees wide, starting at -180
        zone_number = int((longitude + 180) / 6) + 1
        
        # Determine if northern or southern hemisphere
        # For NAD83, we assume northern hemisphere (positive latitude)
        # This could be extended to support southern hemisphere
        return f"EPSG:326{zone_number:02d}"  # WGS 84 / UTM zone {N}

    def latlon_to_utm(
        self,
        latitude: float,
        longitude: float,
    ) -> tuple[float, float]:
        """
        Convert latitude/longitude to UTM coordinates.

        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees

        Returns:
            Tuple of (easting, northing) in meters
        """
        # First transform to WGS84 if needed
        wgs84_lat, wgs84_lon = self._get_transformer().transform(
            longitude, latitude
        )

        # Then transform to appropriate UTM zone
        utm_zone = self._get_utm_zone(wgs84_lon)
        utm_transformer = Transformer.from_crs(
            "EPSG:4326",  # WGS84
            utm_zone,
            always_xy=True,
        )

        easting, northing = utm_transformer.transform(wgs84_lon, wgs84_lat)
        return easting, northing

    def generate_point_number(self, date: datetime, sequence: int) -> str:
        """
        Generate point number in YYMMDDSSSS format.

        Args:
            date: Date for the point (typically from photo EXIF or file date)
            sequence: Sequence number for the day (starting from starting_point_number)

        Returns:
            Point number string like "2602159001"
        """
        # Format: YYMMDD + sequence (9001-9999)
        date_part = date.strftime("%y%m%d")
        return f"{date_part}{sequence}"

    def export(
        self,
        processed_images: list[dict],
        output_path: str,
        base_date: datetime | None = None,
    ) -> str:
        """
        Export processed images to CSV file.

        Args:
            processed_images: List of processed image dicts from ImageProcessor
            output_path: Path to output CSV file
            base_date: Base date for point numbering. If None, uses today's date.
                      If provided, all points use this date.

        Returns:
            Path to created CSV file
        """
        if not processed_images:
            logger.warning("No processed images to export")
            return ""

        # Use provided date or today's date
        if base_date is None:
            base_date = datetime.now()

        # Determine date from first photo if not provided
        # We'll use the base_date for all photos unless we can extract from EXIF
        # For now, use base_date

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        sequence = self.starting_point_number

        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['Point_number', 'Northing', 'Easting', 'Elevation', 'description'])

            for img_data in processed_images:
                gps: GPSData = img_data['gps']
                
                # Convert to UTM
                easting, northing = self.latlon_to_utm(gps.latitude, gps.longitude)
                
                # Get elevation (may be None)
                elevation = gps.altitude if gps.altitude is not None else 0.0
                
                # Generate point number
                point_number = self.generate_point_number(base_date, sequence)
                
                # Get description (use filename if no custom description)
                description = img_data.get('custom_name', img_data['filename'])
                
                # Write row
                writer.writerow([
                    point_number,
                    f"{northing:.4f}",  # Northing to 4 decimal places
                    f"{easting:.4f}",   # Easting to 4 decimal places
                    f"{elevation:.4f}" if elevation else "",
                    description,
                ])
                
                sequence += 1

        logger.info(f"Exported {len(processed_images)} points to {output_file}")
        return str(output_file)
```

**Step 2: Run a simple import test**

Run: `cd /Users/hugochisholm/projects/images2kmz-gv && source .venv/bin/activate && python -c "from images2kmz.csv_exporter import CSVExporter; print('Import OK')"`
Expected: Import OK (may fail if pyproj not installed yet - that's OK for this step)

**Step 3: Commit**

```bash
git add src/images2kmz/csv_exporter.py
git commit -m "feat: add CSV exporter module with UTM conversion"
```

---

## Task 3: Add CLI arguments for CSV export

**Files:**
- Modify: `src/images2kmz/cli.py:91-115` (after log-file argument, before return parser)

**Step 1: Add CLI arguments**

Add this after the `--log-file` argument section and before `return parser`:

```python
# CSV Export options
parser.add_argument(
    '--csv',
    type=str,
    default='',
    help='Output CSV file path for survey data (optional; enables CSV export with UTM coordinates)'
)

parser.add_argument(
    '--coordinate-system',
    type=str,
    default='EPSG:4269',
    help='Coordinate system for UTM conversion (default: EPSG:4269 for NAD83)'
)
```

**Step 2: Test the argument parsing**

Run: `cd /Users/hugochisholm/projects/images2kmz-gv && source .venv/bin/activate && python -m images2kmz --help`
Expected: See the new --csv and --coordinate-system options

**Step 3: Commit**

```bash
git add src/images2kmz/cli.py
git commit -m "feat: add CLI flags for CSV export and coordinate system"
```

---

## Task 4: Integrate CSV export into main CLI flow

**Files:**
- Modify: `src/images2kmz/cli.py:325-382` (after KMZ generation, before final summary)

**Step 1: Add CSV export logic**

After the KMZ generation block (after line ~374 where print_summary is called) and before the except block, add:

```python
# Phase 4: Export CSV if requested
if parsed_args.csv and processed_images:
    console.print(f"\n[bold cyan]📊 Exporting CSV file...[/bold cyan]")
    logger.info(f"Starting CSV export to {parsed_args.csv}")
    
    try:
        from .csv_exporter import CSVExporter
        
        # Determine output path
        if Path(parsed_args.csv).is_absolute():
            csv_path = parsed_args.csv
        else:
            csv_path = str(Path(input_dir) / parsed_args.csv)
        
        exporter = CSVExporter(
            coordinate_system=parsed_args.coordinate_system,
        )
        
        csv_output = exporter.export(
            processed_images=processed_images,
            output_path=csv_path,
        )
        
        if csv_output:
            console.print(f"[green]✓ CSV exported to: {csv_output}[/green]")
            logger.info(f"CSV export complete: {csv_output}")
        else:
            console.print("[yellow]⚠ No data to export to CSV[/yellow]")
            
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}", exc_info=True)
        console.print(f"\n[bold red]Error exporting CSV: {e}[/bold red]")
        # Don't fail the whole operation, just warn
```

**Step 2: Test with a dry run (argument parsing)**

Run: `cd /Users/hugochisholm/projects/images2kmz-gv && source .venv/bin/activate && python -m images2kmz --help`
Expected: New options visible

**Step 3: Commit**

```bash
git add src/images2kmz/cli.py
git commit -m "feat: integrate CSV export into CLI workflow"
```

---

## Task 5: Write tests for CSV exporter

**Files:**
- Create: `tests/test_csv_exporter.py`

**Step 1: Write the test file**

```python
"""Tests for CSV exporter module."""

from __future__ import annotations

import csv
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from images2kmz.csv_exporter import CSVExporter, DEFAULT_COORDINATE_SYSTEM
from images2kmz.image_processor import GPSData


class TestCSVExporter:
    """Tests for CSVExporter class."""

    def test_default_coordinate_system(self):
        """Test default coordinate system is NAD83."""
        exporter = CSVExporter()
        assert exporter.coordinate_system == DEFAULT_COORDINATE_SYSTEM
        assert exporter.coordinate_system == "EPSG:4269"

    def test_custom_coordinate_system(self):
        """Test custom coordinate system can be set."""
        exporter = CSVExporter(coordinate_system="EPSG:4326")
        assert exporter.coordinate_system == "EPSG:4326"

    def test_starting_point_number(self):
        """Test custom starting point number."""
        exporter = CSVExporter(starting_point_number=5001)
        assert exporter.starting_point_number == 5001

    def test_generate_point_number(self):
        """Test point number generation in YYMMDDSSSS format."""
        exporter = CSVExporter(starting_point_number=9001)
        date = datetime(2026, 2, 15)
        
        # First point
        point_num = exporter.generate_point_number(date, 9001)
        assert point_num == "2602159001"
        
        # Sequential points
        point_num2 = exporter.generate_point_number(date, 9002)
        assert point_num2 == "2602159002"

    def test_latlon_to_utm_conversion(self):
        """Test latitude/longitude to UTM conversion."""
        exporter = CSVExporter()
        
        # Test a known location (San Francisco area)
        # NAD83 coordinates
        latitude = 37.7749
        longitude = -122.4194
        
        easting, northing = exporter.latlon_to_utm(latitude, longitude)
        
        # Should get reasonable UTM values
        assert 500000 < easting < 600000  # Around 500k for zone 10
        assert 4100000 < northing < 4200000  # Around 4.1M for zone 10

    def test_export_empty_list(self):
        """Test export with no images returns empty string."""
        exporter = CSVExporter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            result = exporter.export([], str(output_path))
            assert result == ""

    def test_export_single_photo(self):
        """Test exporting a single photo."""
        exporter = CSVExporter()
        
        processed_images = [
            {
                'path': '/path/to/photo.jpg',
                'filename': 'photo.jpg',
                'gps': GPSData(latitude=37.7749, longitude=-122.4194, altitude=10.0),
                'custom_name': 'Test Point',
            }
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            result = exporter.export(processed_images, str(output_path))
            
            assert output_path.exists()
            
            # Read and verify CSV content
            with open(output_path) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
            assert len(rows) == 1
            assert rows[0]['Point_number'] == datetime.now().strftime("%y%m%d") + "9001"
            assert 'Easting' in rows[0]
            assert 'Northing' in rows[0]
            assert rows[0]['description'] == 'Test Point'

    def test_export_multiple_photos_sequential(self):
        """Test sequential point numbering."""
        exporter = CSVExporter(starting_point_number=9001)
        
        base_date = datetime(2026, 2, 15)
        
        processed_images = [
            {
                'path': '/path/photo1.jpg',
                'filename': 'photo1.jpg',
                'gps': GPSData(latitude=37.7749, longitude=-122.4194),
            },
            {
                'path': '/path/photo2.jpg',
                'filename': 'photo2.jpg',
                'gps': GPSData(latitude=37.7750, longitude=-122.4195),
            },
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            exporter.export(processed_images, str(output_path), base_date=base_date)
            
            with open(output_path) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) == 2
            assert rows[0]['Point_number'] == "2602159001"
            assert rows[1]['Point_number'] == "2602159002"


class TestUTMZone:
    """Tests for UTM zone determination."""

    def test_utm_zone_california(self):
        """Test UTM zone for California (longitude ~-122)."""
        exporter = CSVExporter()
        zone = exporter._get_utm_zone(-122.4194)
        assert zone == "EPSG:32610"  # UTM zone 10N

    def test_utm_zone_new_york(self):
        """Test UTM zone for New York (longitude ~-74)."""
        exporter = CSVExporter()
        zone = exporter._get_utm_zone(-74.0060)
        assert zone == "EPSG:32618"  # UTM zone 18N

    def test_utm_zone_uk(self):
        """Test UTM zone for UK (longitude ~0)."""
        exporter = CSVExporter()
        zone = exporter._get_utm_zone(0.0)
        assert zone == "EPSG:32630"  # UTM zone 30N
```

**Step 2: Run tests**

Run: `cd /Users/hugochisholm/projects/images2kmz-gv && source .venv/bin/activate && pip install pyproj && pytest tests/test_csv_exporter.py -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add tests/test_csv_exporter.py
git commit -m "test: add tests for CSV exporter module"
```

---

## Task 6: Install pyproj and verify everything works

**Files:**
- None (just dependency installation)

**Step 1: Install pyproj**

Run: `cd /Users/hugochisholm/projects/images2kmz-gv && source .venv/bin/activate && pip install pyproj`

**Step 2: Run full test suite**

Run: `cd /Users/hugochisholm/projects/images2kmz-gv && source .venv/bin/activate && pytest -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add pyproj dependency"
```

---

## Task 7: Final integration test with sample data (optional)

**Files:**
- None (just testing)

If you have sample geotagged photos, test the full workflow:

```bash
cd /Users/hugochisholm/projects/images2kmz-gv && source .venv/bin/activate
python -m images2kmz /path/to/photos -o output.kmz --csv survey_points.csv
```

Expected: Both KMZ and CSV files created with proper UTM coordinates.

---

## Summary

| Task | Description | Files Changed |
|------|-------------|---------------|
| 1 | Add pyproj dependency | requirements.txt |
| 2 | Create csv_exporter module | src/images2kmz/csv_exporter.py |
| 3 | Add CLI arguments | src/images2kmz/cli.py |
| 4 | Integrate into CLI flow | src/images2kmz/cli.py |
| 5 | Write tests | tests/test_csv_exporter.py |
| 6 | Install and verify | - |

**Plan complete and saved to `docs/plans/2026-02-15-csv-export-feature.md`.**
