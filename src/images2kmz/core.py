from __future__ import annotations

"""Core KMZ generation engine."""

import logging
import tempfile
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType

import simplekml

from .image_processor import GPSData
from .placemark_config import PlacemarkConfig
from .placemark_html_builder import PlacemarkHtmlBuilder
from .utils import get_absolute_path, format_file_size, create_file_uri

logger = logging.getLogger(__name__)


class KMZGenerator(AbstractContextManager):
    """
    KMZ file generator for geotagged photos.

    This class handles creating a KML structure with embedded photo thumbnails
    and links to the original photos.

    Use as a context manager to ensure proper cleanup of temporary files:
        with KMZGenerator(output_path) as kmz:
            kmz.add_photo(...)
            kmz.save()
    """

    def __init__(
        self,
        output_path: str,
        thumbnail_size: tuple[int, int] = (800, 600),
        progress_callback: Callable[[int, int, str], None] | None = None,
        placemark_config: PlacemarkConfig | None = None,
    ):
        """Initialize KMZ generator.

        Args:
            output_path: Path for output KMZ file
            thumbnail_size: Maximum thumbnail dimensions (for reference)
            progress_callback: Optional callback(current, total, filename) for progress tracking
            placemark_config: Configuration for placemark info card fields
        """
        self.output_path = output_path
        self.thumbnail_size = thumbnail_size
        self.kml = simplekml.Kml()
        self.progress_callback = progress_callback
        self.placemark_config = placemark_config or PlacemarkConfig()
        self._html_builder = PlacemarkHtmlBuilder(self.placemark_config)
        self.stats = {
            'photos_added': 0,
            'total_size': 0
        }
        self._temp_dir: tempfile.TemporaryDirectory | None = None

    def __enter__(self) -> KMZGenerator:
        """Enter context manager and create temporary directory."""
        logger.debug("Entering KMZGenerator context manager")
        self._temp_dir = tempfile.TemporaryDirectory()
        logger.debug("Created temporary directory: %s", self._temp_dir.name)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager and clean up temporary directory."""
        if exc_val:
            logger.error("Exception occurred in KMZGenerator context: %s", exc_val, exc_info=True)
        self.cleanup()
    
    def _add_extended_data(
        self,
        pnt,
        abs_photo_path: str,
        gps_data: GPSData,
        description_text: str | None = None,
        bearing: dict | None = None,
    ) -> None:
        """Add ExtendedData elements to placemark for structured display.

        Args:
            pnt: The simplekml Point object
            abs_photo_path: Absolute path to original photo
            gps_data: GPS coordinates
            description_text: Optional description text
            bearing: Optional bearing data
        """
        # Direction (compass bearing)
        if self.placemark_config.show_direction and bearing and bearing.get('raw_text'):
            pnt.extendeddata.newdata(
                name='direction',
                value=bearing['raw_text']
            )

        # Location (coordinates)
        if self.placemark_config.show_location:
            pnt.extendeddata.newdata(
                name='location',
                value=f'{gps_data.latitude:.6f}, {gps_data.longitude:.6f}'
            )

        # Photo path link
        if self.placemark_config.show_photo_path:
            pnt.extendeddata.newdata(
                name='photoPath',
                value=create_file_uri(abs_photo_path)
            )

        # Description
        if self.placemark_config.show_description and description_text:
            # Escape XML characters
            escaped_desc = description_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            pnt.extendeddata.newdata(
                name='description',
                value=escaped_desc
            )
    
    def add_photo(self, photo_path: str, gps_data: GPSData, 
                  thumbnail_bytes: bytes, name: str | None = None,
                  description_text: str | None = None,
                  bearing: dict | None = None) -> None:
        """
        Add a photo to the KMZ file.
        
        Args:
            photo_path: Absolute path to original photo
            gps_data: GPS coordinates for photo
            thumbnail_bytes: Thumbnail image data (JPEG)
            name: Display name for placemark (defaults to filename)
            description_text: Custom description text from EXIF (displayed in bold below thumbnail)
            bearing: Compass bearing data from EXIF (displayed above location)
        """
        # Use filename as default name
        if name is None:
            name = Path(photo_path).name
        
        logger.debug("Adding photo to KMZ: %s", name)
        
        # Get absolute path to original
        abs_photo_path = get_absolute_path(photo_path)
        
        # Add thumbnail to KMZ archive
        # simplekml will handle embedding the image in the KMZ
        # Save thumbnail to temporary file within the managed temp directory
        if self._temp_dir is None:
            logger.error("KMZGenerator used outside context manager")
            raise RuntimeError("KMZGenerator must be used as a context manager (with statement)")

        tmp_path = Path(self._temp_dir.name) / f"thumb_{self.stats['photos_added']}.jpg"
        tmp_path.write_bytes(thumbnail_bytes)
        logger.debug("Wrote thumbnail to temp file: %s (%d bytes)", tmp_path, len(thumbnail_bytes))
        
        # Add the thumbnail to the KMZ
        embedded_path = self.kml.addfile(tmp_path)
        logger.debug("Added thumbnail to KMZ: %s", embedded_path)
        
        # Create placemark at GPS coordinates
        coords = [(gps_data.longitude, gps_data.latitude)]
        if gps_data.altitude is not None:
            coords = [(gps_data.longitude, gps_data.latitude, gps_data.altitude)]
        
        pnt = self.kml.newpoint(name=name, coords=coords)
        
        # Set icon based on photo bearing
        if bearing and bearing.get('azimuth') is not None:
            # Use directional track icon with rotation
            pnt.style.iconstyle.icon.href = 'http://earth.google.com/images/kml-icons/track-directional/track-0.png'
            pnt.style.iconstyle.heading = bearing['azimuth']
            pnt.style.iconstyle.scale = 1.4
        else:
            # Use non-directional track icon
            pnt.style.iconstyle.icon.href = 'http://earth.google.com/images/kml-icons/track-directional/track-none.png'
            pnt.style.iconstyle.scale = 1.4
        
        # Generate description using HTML builder
        pnt.description = self._html_builder.build(
            embedded_path=embedded_path,
            abs_photo_path=abs_photo_path,
            gps_data=gps_data,
            description_text=description_text,
            bearing=bearing
        )
        
        # Add ExtendedData for structured info display in balloon
        self._add_extended_data(
            pnt=pnt,
            abs_photo_path=abs_photo_path,
            gps_data=gps_data,
            description_text=description_text,
            bearing=bearing
        )
        
        # Track stats
        self.stats['photos_added'] += 1
        self.stats['total_size'] += len(thumbnail_bytes)
        logger.info("Added photo '%s' at coordinates (%.6f, %.6f)", name, gps_data.latitude, gps_data.longitude)
    
    def cleanup(self) -> None:
        """Clean up temporary directory and all its contents."""
        if self._temp_dir is not None:
            logger.debug("Cleaning up temporary directory: %s", self._temp_dir.name)
            try:
                self._temp_dir.cleanup()
                logger.debug("Successfully cleaned up temporary directory")
            except Exception as e:
                logger.warning("Failed to clean up temporary directory: %s", e)
            finally:
                self._temp_dir = None
    
    def save(self) -> str:
        """
        Save the KMZ file.
        
        Returns:
            Absolute path to saved KMZ file
        """
        logger.info("Saving KMZ file to: %s", self.output_path)
        try:
            # Ensure output directory exists
            output_path = Path(self.output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            logger.debug("Ensured output directory exists: %s", output_path.parent)
            
            # Save as KMZ (compressed KML with embedded files)
            self.kml.savekmz(self.output_path)
            
            final_path = get_absolute_path(self.output_path)
            file_size = output_path.stat().st_size
            logger.info("Successfully saved KMZ file: %s (%d bytes)", final_path, file_size)
            
            return final_path
        except Exception as e:
            logger.error("Failed to save KMZ file: %s", e, exc_info=True)
            raise
        finally:
            self.cleanup()
    
    def get_stats(self) -> dict[str, int]:
        """
        Get generation statistics.
        
        Returns:
            Dict with 'photos_added' and 'total_size' keys
        """
        return self.stats.copy()
    
    def get_file_size(self) -> int | None:
        """
        Get size of generated KMZ file.
        
        Returns:
            File size in bytes, or None if file doesn't exist yet
        """
        output_path = Path(self.output_path)
        if output_path.exists():
            return output_path.stat().st_size
        return None
    
    def get_formatted_file_size(self) -> str | None:
        """
        Get formatted size of generated KMZ file.
        
        Returns:
            Formatted file size string (e.g., "2.4 MB"), or None if file doesn't exist
        """
        size = self.get_file_size()
        if size is not None:
            return format_file_size(size)
        return None
