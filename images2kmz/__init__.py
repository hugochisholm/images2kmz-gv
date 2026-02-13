"""
images2kmz - Create KMZ files from geotagged photos.

This package provides tools to scan directories for geotagged photos,
extract GPS coordinates, create thumbnails, and generate KMZ files
suitable for viewing in Google Earth and other mapping applications.
"""

__version__ = '0.2.0'
__author__ = 'Hugo Chisholm'
__license__ = 'MIT'

# Core functionality
from .core import KMZGenerator
from .image_processor import (
    ImageProcessor,
    GPSData,
    extract_gps_data,
    create_thumbnail,
    get_image_files,
    is_supported_format
)
from .heic_handler import (
    HEICHandler,
    find_heic_files,
    convert_heic_to_jpg,
    batch_convert_heic
)
from .utils import (
    get_absolute_path,
    create_file_uri,
    ensure_directory_exists,
    format_file_size
)

# CLI
from .cli import run, main

__all__ = [
    # Core
    'KMZGenerator',
    # Image processing
    'ImageProcessor',
    'GPSData',
    'extract_gps_data',
    'create_thumbnail',
    'get_image_files',
    'is_supported_format',
    # HEIC handling
    'HEICHandler',
    'find_heic_files',
    'convert_heic_to_jpg',
    'batch_convert_heic',
    # Utilities
    'get_absolute_path',
    'create_file_uri',
    'ensure_directory_exists',
    'format_file_size',
    # CLI
    'run',
    'main',
]
