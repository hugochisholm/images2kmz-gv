"""Image processing functions for extracting GPS data and creating thumbnails."""

import os
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from io import BytesIO

from PIL import Image
from GPSPhoto import gpsphoto


# Supported image formats
SUPPORTED_FORMATS = ('.jpg', '.jpeg')


class GPSData:
    """Container for GPS coordinates."""
    
    def __init__(self, latitude: float, longitude: float, altitude: Optional[float] = None):
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
    
    def __repr__(self) -> str:
        return f"GPSData(lat={self.latitude}, lon={self.longitude}, alt={self.altitude})"


def extract_gps_data(image_path: str) -> Optional[GPSData]:
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


def create_thumbnail(image_path: str, max_size: Tuple[int, int] = (800, 600)) -> bytes:
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


def extract_custom_pin_name(image_path: str, fallback_name: str) -> Tuple[str, Optional[str]]:
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


def is_supported_format(file_path: str) -> bool:
    """
    Check if file is a supported image format.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if file extension is supported
    """
    return file_path.lower().endswith(SUPPORTED_FORMATS)


def get_image_files(directory: str, recursive: bool = False) -> List[str]:
    """
    Get list of supported image files in a directory.
    
    Args:
        directory: Directory path to search
        recursive: If True, search subdirectories recursively
        
    Returns:
        List of absolute paths to image files
    """
    image_files = []
    
    if recursive:
        # Walk directory tree
        for root, _, files in os.walk(directory):
            for filename in files:
                if is_supported_format(filename):
                    image_files.append(os.path.join(root, filename))
    else:
        # Only top-level directory
        try:
            for item in os.listdir(directory):
                path = os.path.join(directory, item)
                if os.path.isfile(path) and is_supported_format(item):
                    image_files.append(path)
        except (PermissionError, FileNotFoundError):
            pass
    
    return sorted(image_files)


class ImageProcessor:
    """High-level image processing coordinator."""
    
    def __init__(self, thumbnail_size: Tuple[int, int] = (800, 600)):
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
    
    def process_directory(self, directory: str, recursive: bool = False) -> List[Dict]:
        """
        Process all images in a directory.
        
        Args:
            directory: Directory to scan
            recursive: Search recursively
            
        Returns:
            List of dicts with processed image info:
            {
                'path': str,
                'filename': str,
                'gps': GPSData,
                'thumbnail': bytes,
                'custom_name': str,
                'description_text': Optional[str]
            }
        """
        image_files = get_image_files(directory, recursive)
        self.stats['total_found'] = len(image_files)
        
        processed_images = []
        
        for image_path in image_files:
            try:
                # Extract GPS data
                gps_data = extract_gps_data(image_path)
                
                if gps_data is None:
                    self.stats['skipped_no_gps'] += 1
                    continue
                
                # Create thumbnail
                thumbnail_bytes = create_thumbnail(image_path, self.thumbnail_size)
                
                # Get filename
                filename = os.path.basename(image_path)
                
                # Extract custom pin name and description from EXIF
                custom_name, description_text = extract_custom_pin_name(image_path, filename)
                
                processed_images.append({
                    'path': image_path,
                    'filename': filename,
                    'gps': gps_data,
                    'thumbnail': thumbnail_bytes,
                    'custom_name': custom_name,
                    'description_text': description_text
                })
                
                self.stats['processed'] += 1
                
            except Exception as e:
                self.stats['errors'] += 1
                # Silently skip files with errors
                continue
        
        return processed_images
    
    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics."""
        return self.stats.copy()
