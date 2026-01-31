"""Core KMZ generation engine."""

import os
import tempfile
from typing import Dict, Optional, Tuple, List
import simplekml

from .image_processor import GPSData
from .utils import get_absolute_path, format_file_size


class KMZGenerator:
    """
    KMZ file generator for geotagged photos.
    
    This class handles creating a KML structure with embedded photo thumbnails
    and links to the original photos.
    """
    
    def __init__(self, output_path: str, thumbnail_size: Tuple[int, int] = (640, 480)):
        """
        Initialize KMZ generator.
        
        Args:
            output_path: Path for output KMZ file
            thumbnail_size: Maximum thumbnail dimensions (for reference)
        """
        self.output_path = output_path
        self.thumbnail_size = thumbnail_size
        self.kml = simplekml.Kml()
        self.stats = {
            'photos_added': 0,
            'total_size': 0
        }
        self._temp_files: List[str] = []  # Track temp files to clean up later
    
    def add_photo(self, photo_path: str, gps_data: GPSData, 
                  thumbnail_bytes: bytes, name: Optional[str] = None) -> None:
        """
        Add a photo to the KMZ file.
        
        Args:
            photo_path: Absolute path to original photo
            gps_data: GPS coordinates for photo
            thumbnail_bytes: Thumbnail image data (JPEG)
            name: Display name for placemark (defaults to filename)
        """
        # Use filename as default name
        if name is None:
            name = os.path.basename(photo_path)
        
        # Get absolute path to original
        abs_photo_path = get_absolute_path(photo_path)
        
        # Add thumbnail to KMZ archive
        # simplekml will handle embedding the image in the KMZ
        # Save thumbnail to temporary file (will be cleaned up after KMZ is saved)
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp.write(thumbnail_bytes)
            tmp_path = tmp.name
        
        # Track temp file for cleanup later
        self._temp_files.append(tmp_path)
        
        # Add the thumbnail to the KMZ
        embedded_path = self.kml.addfile(tmp_path)
        
        # Create placemark at GPS coordinates
        coords = [(gps_data.longitude, gps_data.latitude)]
        if gps_data.altitude is not None:
            coords = [(gps_data.longitude, gps_data.latitude, gps_data.altitude)]
        
        pnt = self.kml.newpoint(name=name, coords=coords)
        
        # Create description with embedded thumbnail and link to original
        description = f'''
        <![CDATA[
        <div style="font-family: Arial, sans-serif;">
            <img src="{embedded_path}" style="max-width: 640px; max-height: 480px; width: auto; height: auto;" /><br/>
            <p style="margin-top: 10px;">
                <a href="file://{abs_photo_path}" target="_blank">Open Original Photo</a>
            </p>
            <p style="font-size: 0.9em; color: #666;">
                Location: {gps_data.latitude:.6f}, {gps_data.longitude:.6f}
            </p>
        </div>
        ]]>
        '''
        
        pnt.description = description
        
        # Track stats
        self.stats['photos_added'] += 1
        self.stats['total_size'] += len(thumbnail_bytes)
    
    def save(self) -> str:
        """
        Save the KMZ file.
        
        Returns:
            Absolute path to saved KMZ file
        """
        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(self.output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # Save as KMZ (compressed KML with embedded files)
            self.kml.savekmz(self.output_path)
            
            return get_absolute_path(self.output_path)
        finally:
            # Clean up temporary files
            for tmp_file in self._temp_files:
                try:
                    os.unlink(tmp_file)
                except Exception:
                    pass
            self._temp_files.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get generation statistics.
        
        Returns:
            Dict with 'photos_added' and 'total_size' keys
        """
        return self.stats.copy()
    
    def get_file_size(self) -> Optional[int]:
        """
        Get size of generated KMZ file.
        
        Returns:
            File size in bytes, or None if file doesn't exist yet
        """
        if os.path.exists(self.output_path):
            return os.path.getsize(self.output_path)
        return None
    
    def get_formatted_file_size(self) -> Optional[str]:
        """
        Get formatted size of generated KMZ file.
        
        Returns:
            Formatted file size string (e.g., "2.4 MB"), or None if file doesn't exist
        """
        size = self.get_file_size()
        if size is not None:
            return format_file_size(size)
        return None
