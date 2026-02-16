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
        assert zone == "EPSG:32631"  # UTM zone 31N
