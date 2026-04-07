from __future__ import annotations

"""Image processing functions for extracting GPS data and creating thumbnails."""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from collections.abc import Callable

from PIL import Image
from GPSPhoto import gpsphoto

logger = logging.getLogger(__name__)


# Supported image formats
SUPPORTED_FORMATS = ('.jpg', '.jpeg')

THUMBNAIL_PRESETS = {
    'small': (800, 800),
    'medium': (1200, 1200),
    'large': (1800, 1800)
}


@dataclass
class GPSData:
    """Container for GPS coordinates."""
    
    latitude: float
    longitude: float
    altitude: float | None = None
    
    def __repr__(self) -> str:
        return f"GPSData(lat={self.latitude}, lon={self.longitude}, alt={self.altitude})"


def extract_gps_data(image_path: str) -> GPSData | None:
    """
    Extract GPS coordinates from image EXIF data.
    
    Args:
        image_path: Path to image file
        
    Returns:
        GPSData object if GPS data found, None otherwise
    """
    try:
        data = gpsphoto.getGPSData(image_path)
        
        if data and 'Latitude' in data and 'Longitude' in data:
            altitude = data.get('Altitude')
            gps_data = GPSData(
                latitude=data['Latitude'],
                longitude=data['Longitude'],
                altitude=altitude
            )
            logger.debug(f"GPS data extracted from {image_path}: {gps_data}")
            return gps_data
        logger.debug(f"No GPS data found in {image_path}")
        return None
    except Exception as e:
        logger.warning(f"Error extracting GPS data from {image_path}: {e}")
        return None


def create_thumbnail(image_path: str, max_size: tuple[int, int] = (800, 600)) -> bytes:
    """
    Create a thumbnail of an image while maintaining aspect ratio.
    
    Args:
        image_path: Path to source image
        max_size: Maximum dimensions (width, height) for thumbnail
        
    Returns:
        Thumbnail image as bytes (JPEG format)
    """
    logger.debug(f"Creating thumbnail for {image_path} with max size {max_size}")
    try:
        with Image.open(image_path) as img:
            original_size = img.size
            # Handle EXIF orientation
            try:
                from PIL import ImageOps
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass
            
            # Create thumbnail maintaining aspect ratio
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary (handles RGBA, P, etc.)
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            # Save to bytes buffer
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85, optimize=True)
            thumbnail_size = buffer.tell()
            logger.debug(f"Thumbnail created for {image_path}: {original_size} -> ~{img.size} ({thumbnail_size} bytes)")
            return buffer.getvalue()
    except Exception as e:
        logger.error(f"Failed to create thumbnail for {image_path}: {e}")
        raise


def extract_capture_date(image_path: str) -> datetime | None:
    """Extract capture date from image EXIF, fallback to file mod time."""
    try:
        import exifread
        with open(image_path, "rb") as f:
            tags = exifread.process_file(f, details=False)
            
        date_tags = ["EXIF DateTimeOriginal", "Image DateTime", "EXIF DateTimeDigitized"]
        for tag in date_tags:
            if tag in tags:
                date_str = str(tags[tag])
                try:
                    from datetime import datetime
                    return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    pass
    except Exception as e:
        logger.debug(f"Failed to read EXIF date from {image_path}: {e}")
        
    try:
        from datetime import datetime
        timestamp = os.path.getmtime(image_path)
        return datetime.fromtimestamp(timestamp)
    except Exception:
        return None


def extract_custom_pin_name(image_path: str, fallback_name: str) -> tuple[str, str | None]:
    """
    Extract custom pin name and description from EXIF ImageDescription.
    
    Looks for EXIF ImageDescription starting with "GeoVerra, Nav Photo - ".
    If found, extracts the part after the prefix as both:
    - Pin name (truncated to 25 chars with "...")
    - Full description text (newlines replaced with " - ")
    
    Args:
        image_path: Path to image file
        fallback_name: Filename to use if custom name not found
        
    Returns:
        Tuple of (pin_name, description_text) where description_text is None
        if the EXIF pattern wasn't found or if ImageDescription is empty
    """
    try:
        import exifread
        
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
        
        if not tags:
            return fallback_name, None
        
        # Tag 270 = ImageDescription (in '0th' IFD)
        description_tag = tags.get('Image ImageDescription')
        
        if not description_tag:
            return fallback_name, None
        
        # Convert to string - exifread returns printable objects
        description = str(description_tag)
        
        # Return if empty after stripping
        if not description:
            return fallback_name, None
        
        # Check for GeoVerra pattern
        prefix = 'GeoVerra, Nav Photo - '
        if not description.startswith(prefix):
            return fallback_name, None
        
        # Extract the part after the prefix
        extracted = description[len(prefix):]
        
        # Replace newlines with ' - ' for both pin name and description
        extracted = extracted.replace('\n', ' - ').replace('\r', '')
        
        # Create pin name (25 chars max with "...")
        pin_name = (extracted[:25] + '...') if len(extracted) > 25 else extracted
        
        # Return both the truncated name and full description
        return pin_name, extracted
        
    except Exception:
        # Silent failure - return fallback
        return fallback_name, None


def get_compass_bearing(image_path: str) -> dict | None:
    """
    Extract compass bearing from EXIF GPS image direction data.
    
    Converts GPSImgDirection (as a ratio) to compass bearing with 8-point
    cardinal direction and azimuth in degrees.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Dictionary with bearing data:
        {
            'azimuth': int,        # 0-359 degrees (rounded)
            'compass': str,        # 'N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'
            'reference': Optional[str],  # 'Mag' or 'True' (None if not specified)
            'raw_text': str        # e.g., 'NW 316° Mag' or 'NE 45°'
        }
        Returns None if no bearing data found in EXIF
    """
    try:
        import exifread
        
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
        
        if not tags:
            return None
        
        # Tag 17 = GPSImgDirection (in GPS IFD)
        direction_tag = tags.get('GPS GPSImgDirection')
        
        if not direction_tag:
            return None
        
        # Extract direction ratio - exifread returns strings like "1297996/3681"
        # Convert to float degrees
        try:
            # Handle Ratio type from exifread
            if hasattr(direction_tag, 'values'):
                # It's an IfdTag with values list containing a ratio string
                values = direction_tag.values
                if values and len(values) >= 1:
                    # Values contains strings like "1297996/3681"
                    ratio_str = str(values[0])
                    if '/' in ratio_str:
                        numerator, denominator = ratio_str.split('/')
                        numerator = float(numerator)
                        denominator = float(denominator)
                        if denominator == 0:
                            return None
                        degrees = numerator / denominator
                    else:
                        # Already a plain number
                        degrees = float(ratio_str)
                else:
                    return None
            else:
                # Try direct conversion
                degrees = float(direction_tag)
        except (TypeError, ValueError, ZeroDivisionError):
            return None
        
        # Round to nearest integer and normalize to 0-359
        azimuth = int(round(degrees)) % 360
        
        # Get reference (Tag 16 = GPSImgDirectionRef)
        reference_text = None
        ref_tag = tags.get('GPS GPSImgDirectionRef')
        if ref_tag:
            ref_value = str(ref_tag).strip()
            if ref_value == 'T':
                reference_text = 'True'
            elif ref_value == 'M':
                reference_text = 'Mag'
        
        # Convert azimuth to 8-point compass
        compass_directions = {
            'N': (337.5, 22.5),
            'NE': (22.5, 67.5),
            'E': (67.5, 112.5),
            'SE': (112.5, 157.5),
            'S': (157.5, 202.5),
            'SW': (202.5, 247.5),
            'W': (247.5, 292.5),
            'NW': (292.5, 337.5),
        }
        
        compass_dir = 'N'  # Default
        for direction, (min_angle, max_angle) in compass_directions.items():
            if direction == 'N':
                # N wraps around 360/0
                if azimuth >= min_angle or azimuth < max_angle:
                    compass_dir = direction
                    break
            else:
                if min_angle <= azimuth < max_angle:
                    compass_dir = direction
                    break
        
        # Build raw text
        if reference_text:
            raw_text = f'{compass_dir} {azimuth}° {reference_text}'
        else:
            raw_text = f'{compass_dir} {azimuth}°'
        
        return {
            'azimuth': azimuth,
            'compass': compass_dir,
            'reference': reference_text,
            'raw_text': raw_text
        }
        
    except Exception:
        # Silent failure - return None
        return None


def is_supported_format(file_path: str) -> bool:
    """
    Check if file is a supported image format.

    Args:
        file_path: Path to file

    Returns:
        True if file extension is supported
    """
    return file_path.lower().endswith(SUPPORTED_FORMATS)


def _process_single_image(args: tuple[str, str]) -> dict | None:
    """Process a single image - helper function for parallel processing.

    Args:
        args: Tuple of (image_path, thumbnail_size_preset)

    Returns:
        Dict with processed image info or None if processing failed
    """
    image_path, thumbnail_size_preset = args

    try:
        # Extract GPS data
        gps_data = extract_gps_data(image_path)

        if gps_data is None:
            return {'skipped': True, 'path': image_path, 'reason': 'no_gps'}

        # Create thumbnail
        thumbnail_dimensions = THUMBNAIL_PRESETS[thumbnail_size_preset]
        thumbnail_bytes = create_thumbnail(image_path, thumbnail_dimensions)

        # Get filename
        filename = Path(image_path).name

        # Extract custom pin name and description from EXIF
        custom_name, description_text = extract_custom_pin_name(image_path, filename)

        # Extract compass bearing from EXIF
        bearing = get_compass_bearing(image_path)
        
        # Extract capture date
        capture_date = extract_capture_date(image_path)

        return {
            'path': image_path,
            'filename': filename,
            'gps': gps_data,
            'thumbnail': thumbnail_bytes,
            'custom_name': custom_name,
            'description_text': description_text,
            'bearing': bearing,
            'capture_date': capture_date
        }

    except Exception as e:
        return {'error': True, 'path': image_path, 'error_message': str(e)}


def get_image_files(directory: str, recursive: bool = False) -> list[str]:
    """
    Get list of supported image files in a directory.
    
    Args:
        directory: Directory path to search
        recursive: If True, search subdirectories recursively
        
    Returns:
        List of absolute paths to image files
    """
    image_files = []
    dir_path = Path(directory)

    if recursive:
        # Walk directory tree using pathlib
        for file_path in dir_path.rglob('*'):
            if file_path.is_file() and is_supported_format(str(file_path)):
                image_files.append(str(file_path))
    else:
        # Only top-level directory
        try:
            for file_path in dir_path.iterdir():
                if file_path.is_file() and is_supported_format(file_path.name):
                    image_files.append(str(file_path))
        except (PermissionError, FileNotFoundError):
            pass

    return sorted(image_files)


class ImageProcessor:
    """High-level image processing coordinator."""

    def __init__(self, thumbnail_size: str = 'medium'):
        """
        Initialize image processor.

        Args:
            thumbnail_size: Preset size for thumbnails ('small', 'medium', 'large')
        """
        if thumbnail_size not in THUMBNAIL_PRESETS:
            raise KeyError(f"Invalid thumbnail size preset: {thumbnail_size}. Must be one of: {list(THUMBNAIL_PRESETS.keys())}")
        self.thumbnail_size = thumbnail_size
        self.stats = {
            'total_found': 0,
            'processed': 0,
            'skipped_no_gps': 0,
            'errors': 0
        }
        self.errors: list[dict] = []  # Collect errors for end-of-run reporting
        self.no_gps: list[str] = []  # Files without GPS data
        self.no_direction: list[str] = []  # Files without direction/bearing data
    
    def process_directory(
        self,
        directory: str,
        recursive: bool = False,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[dict]:
        """
        Process all images in a directory using parallel processing.

        Args:
            directory: Directory to scan
            recursive: Search recursively
            progress_callback: Optional callback(current, total, filename) for progress tracking

        Returns:
            List of dicts with processed image info:
            {
                'path': str,
                'filename': str,
                'gps': GPSData,
                'thumbnail': bytes,
                'custom_name': str,
                'description_text': Optional[str],
                'bearing': Optional[Dict]
            }
        """
        image_files = get_image_files(directory, recursive)
        self.stats['total_found'] = len(image_files)
        self.errors = []  # Reset error collection

        logger.info(f"Starting processing of {len(image_files)} image(s) in '{directory}' (recursive={recursive})")

        processed_images = []
        completed = 0

        # Prepare arguments for parallel processing
        process_args = [(path, self.thumbnail_size) for path in image_files]

        for args in process_args:
            completed += 1
            image_path = args[0]
            filename = Path(image_path).name

            result = _process_single_image(args)

            if result is None:
                self.stats['errors'] += 1
                error_msg = 'Unknown error during processing'
                self.errors.append({'path': image_path, 'error': error_msg})
                logger.warning(f"Failed to process {filename}: {error_msg}")
            elif result.get('skipped'):
                self.stats['skipped_no_gps'] += 1
                self.no_gps.append(filename)
                logger.debug(f"Skipped {filename}: no GPS data")
            elif result.get('error'):
                self.stats['errors'] += 1
                error_msg = result.get('error_message', 'Unknown error')
                self.errors.append({'path': image_path, 'error': error_msg})
                logger.error(f"Failed to process {filename}: {error_msg}")
            else:
                self.stats['processed'] += 1
                if 'bearing' not in result or result['bearing'] is None:
                    self.no_direction.append(filename)
                processed_images.append(result)

            # Fire progress callback
            if progress_callback:
                progress_callback(completed, len(image_files), filename)

        return processed_images
    def get_stats(self) -> dict[str, int]:
        """Get processing statistics."""
        return self.stats.copy()
    
    def get_no_gps(self) -> list[str]:
        """Get list of filenames without GPS data."""
        return self.no_gps.copy()
    
    def get_no_direction(self) -> list[str]:
        """Get list of filenames without direction data."""
        return self.no_direction.copy()
