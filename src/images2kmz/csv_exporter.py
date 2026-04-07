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
        self._last_utm_zone: str | None = None

    def get_coordinate_info(self) -> str:
        """Get a description of the coordinate system used."""
        return self.coordinate_system

    def get_utm_zone_info(self) -> str | None:
        """Get the UTM zone used for the last conversion."""
        return self._last_utm_zone

    def _get_transformer(self) -> Transformer:
        """Get or create the coordinate transformer."""
        if self._transformer is None:
            # Transform from source CRS to WGS84 (EPSG:4326)
            # GPS coordinates from photos are typically in WGS84
            self._transformer = Transformer.from_crs(
                self.coordinate_system,
                "EPSG:4326",  # WGS84
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
        # Zone 1: -180 to -174
        # Zone 31: -6 to 0 (UK starts around -8, so zone 30)
        # Zone 32: 0 to 6
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
        # Determine UTM zone from longitude
        utm_zone = self._get_utm_zone(longitude)
        self._last_utm_zone = utm_zone

        # Transform directly to UTM from source CRS
        # Most GPS data from photos is in WGS84, so this handles that case
        # For NAD83, the transformation will handle the datum shift if needed
        utm_transformer = Transformer.from_crs(
            self.coordinate_system,
            utm_zone,
            always_xy=True,
        )

        easting, northing = utm_transformer.transform(longitude, latitude)
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

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        sequence = self.starting_point_number

        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)

            for img_data in processed_images:
                gps: GPSData = img_data['gps']

                # Convert to UTM
                easting, northing = self.latlon_to_utm(gps.latitude, gps.longitude)

                # Get elevation (may be None)
                elevation = gps.altitude if gps.altitude is not None else 0.0

                # Generate point number
                photo_date = img_data.get('capture_date') or base_date
                point_number = self.generate_point_number(photo_date, sequence)

                # Get description: "PHOTO($azimuth) $photo_description"
                photo_desc = img_data.get('description_text') or img_data.get('custom_name', img_data['filename'])
                bearing_data = img_data.get('bearing')
                if bearing_data and 'azimuth' in bearing_data:
                    azimuth = bearing_data['azimuth']
                    description = f"PHOTO({azimuth}) {photo_desc}"
                else:
                    description = f"PHOTO {photo_desc}"

                # Write row
                writer.writerow([
                    point_number,
                    f"{northing:.4f}",  # Northing to 4 decimal places
                    f"{easting:.4f}",   # Easting to 4 decimal places
                    f"{elevation:.4f}",  # Elevation always present (0 if none)
                    description,
                ])

                sequence += 1

        logger.info(f"Exported {len(processed_images)} points to {output_file}")
        return str(output_file)
