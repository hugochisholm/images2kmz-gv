from __future__ import annotations

"""Image processing functions for extracting GPS data and creating thumbnails."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from collections.abc import Callable

from PIL import Image
from GPSPhoto import gpsphoto


# Supported image formats
SUPPORTED_FORMATS = ('.jpg', '.jpeg')


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
            return GPSData(
                latitude=data['Latitude'],
                longitude=data['Longitude'],
                altitude=altitude
            )
        return None
    except Exception as e:
        # If there's any error reading GPS data, return None
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
    with Image.open(image_path) as img:
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
        return buffer.getvalue()


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
        import piexif
        
        with Image.open(image_path) as img:
            exif_data = img.info.get('exif')
            if not exif_data:
                return fallback_name, None
            
            exif_dict = piexif.load(exif_data)
            
            # Tag 270 = ImageDescription (in '0th' IFD)
            description = None
            if '0th' in exif_dict:
                description = exif_dict['0th'].get(270)
            
            if not description:
                return fallback_name, None
            
            # Decode if bytes
            if isinstance(description, bytes):
                description = description.decode('utf-8', errors='ignore').strip()
            
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
        import piexif
        
        with Image.open(image_path) as img:
            exif_data = img.info.get('exif')
            if not exif_data:
                return None
            
            exif_dict = piexif.load(exif_data)
            
            # Get GPS IFD
            if 'GPS' not in exif_dict:
                return None
            
            gps_ifd = exif_dict['GPS']
            
            # Tag 17 = GPSImgDirection (as ratio/fraction)
            if 17 not in gps_ifd:
                return None
            
            # Extract direction ratio
            direction_ratio = gps_ifd[17]
            if not direction_ratio or len(direction_ratio) != 2:
                return None
            
            numerator, denominator = direction_ratio
            
            # Avoid division by zero
            if denominator == 0:
                return None
            
            # Convert ratio to degrees
            degrees = float(numerator) / float(denominator)
            
            # Round to nearest integer and normalize to 0-359
            azimuth = int(round(degrees)) % 360
            
            # Get reference (Tag 16 = GPSImgDirectionRef)
            reference_text = None
            if 16 in gps_ifd:
                reference_raw = gps_ifd[16]
                if isinstance(reference_raw, bytes):
                    reference_raw = reference_raw.decode('utf-8', errors='ignore').strip()
                
                if reference_raw == 'T':
                    reference_text = 'True'
                elif reference_raw == 'M':
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
    
    def __init__(self, thumbnail_size: tuple[int, int] = (800, 600)):
        """
        Initialize image processor.
        
        Args:
            thumbnail_size: Maximum dimensions for thumbnails
        """
        self.thumbnail_size = thumbnail_size
        self.stats = {
            'total_found': 0,
            'processed': 0,
            'skipped_no_gps': 0,
            'errors': 0
        }
    
    def process_directory(
        self,
        directory: str,
        recursive: bool = False,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[dict]:
        """
        Process all images in a directory.
        
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
        
        processed_images = []
        
        for index, image_path in enumerate(image_files, 1):
            try:
                # Extract GPS data
                gps_data = extract_gps_data(image_path)
                
                if gps_data is None:
                    self.stats['skipped_no_gps'] += 1
                    continue
                
                # Create thumbnail
                thumbnail_bytes = create_thumbnail(image_path, self.thumbnail_size)
                
                # Get filename
                filename = Path(image_path).name
                
                # Extract custom pin name and description from EXIF
                custom_name, description_text = extract_custom_pin_name(image_path, filename)
                
                # Extract compass bearing from EXIF
                bearing = get_compass_bearing(image_path)
                
                processed_images.append({
                    'path': image_path,
                    'filename': filename,
                    'gps': gps_data,
                    'thumbnail': thumbnail_bytes,
                    'custom_name': custom_name,
                    'description_text': description_text,
                    'bearing': bearing
                })
                
                self.stats['processed'] += 1
                
                # Fire progress callback
                if progress_callback:
                    progress_callback(index, len(image_files), filename)
                
            except Exception as e:
                self.stats['errors'] += 1
                # Silently skip files with errors
                continue
        
        return processed_images
    
    def get_stats(self) -> dict[str, int]:
        """Get processing statistics."""
        return self.stats.copy()
