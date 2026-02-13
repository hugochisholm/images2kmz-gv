"""HEIC file detection and conversion to JPEG."""

import os
import shutil
from pathlib import Path
from typing import List, Optional

from PIL import Image
from pillow_heif import register_heif_opener

# Initialize HEIC support
register_heif_opener()

HEIC_EXTENSIONS = ('.heic', '.heif')


def find_heic_files(directory: str, recursive: bool = False) -> List[str]:
    """
    Find all HEIC/HEIF files in a directory.
    
    Args:
        directory: Directory to search
        recursive: Search subdirectories recursively
        
    Returns:
        List of absolute paths to HEIC files
    """
    heic_files = []
    
    if recursive:
        for root, _, files in os.walk(directory):
            for filename in files:
                if filename.lower().endswith(HEIC_EXTENSIONS):
                    heic_files.append(os.path.join(root, filename))
    else:
        try:
            for item in os.listdir(directory):
                path = os.path.join(directory, item)
                if os.path.isfile(path) and item.lower().endswith(HEIC_EXTENSIONS):
                    heic_files.append(path)
        except (PermissionError, FileNotFoundError):
            pass
    
    return sorted(heic_files)


def convert_heic_to_jpg(heic_path: str, output_dir: Optional[str] = None) -> Optional[str]:
    """
    Convert a single HEIC file to JPEG, preserving EXIF metadata.
    
    Preserves all EXIF data including GPS information, camera metadata, and orientation.
    
    Args:
        heic_path: Path to HEIC file
        output_dir: Directory for output JPG (defaults to same directory as input)
        
    Returns:
        Path to created JPG file, or None if conversion failed
    """
    try:
        # Determine output path
        if output_dir is None:
            output_dir = os.path.dirname(heic_path)
        
        # Create output filename (replace extension with .jpg)
        base_name = os.path.splitext(os.path.basename(heic_path))[0]
        jpg_path = os.path.join(output_dir, f"{base_name}.jpg")
        
        # Open and convert
        with Image.open(heic_path) as img:
            # Extract EXIF data BEFORE any image modifications
            exif_data = img.info.get('exif')
            
            # Handle EXIF orientation
            try:
                from PIL import ImageOps
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass
            
            # Convert to RGB if necessary
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            # Save as JPEG with EXIF data preserved
            if exif_data:
                img.save(jpg_path, 'JPEG', quality=95, optimize=True, exif=exif_data)
            else:
                img.save(jpg_path, 'JPEG', quality=95, optimize=True)
        
        return jpg_path
        
    except Exception as e:
        print(f"Error converting {heic_path}: {e}")
        return None


def batch_convert_heic(heic_files: List[str], output_dir: Optional[str] = None, 
                       move_originals: bool = False, originals_dir: str = "HEIC originals") -> List[str]:
    """
    Convert multiple HEIC files to JPEG.
    
    Args:
        heic_files: List of HEIC file paths
        output_dir: Directory for output JPG files
        move_originals: If True, move original HEIC files to a subdirectory
        originals_dir: Name of subdirectory for original HEIC files
        
    Returns:
        List of successfully converted JPG file paths
    """
    converted_files = []
    
    for heic_path in heic_files:
        jpg_path = convert_heic_to_jpg(heic_path, output_dir)
        
        if jpg_path:
            converted_files.append(jpg_path)
            print(f"  {os.path.basename(heic_path)} → {os.path.basename(jpg_path)}")
        else:
            print(f"  Failed: {os.path.basename(heic_path)}")
    
    # Move original HEIC files if requested
    if move_originals and converted_files:
        # Determine where to create the originals directory
        if heic_files:
            first_file_dir = os.path.dirname(heic_files[0])
            originals_path = os.path.join(first_file_dir, originals_dir)
            
            # Create directory
            os.makedirs(originals_path, exist_ok=True)
            
            # Move files
            for heic_path in heic_files:
                try:
                    dest_path = os.path.join(originals_path, os.path.basename(heic_path))
                    shutil.move(heic_path, dest_path)
                except Exception as e:
                    print(f"  Warning: Could not move {os.path.basename(heic_path)}: {e}")
            
            print(f"Moved {len(heic_files)} original HEIC files to '{originals_dir}/'")
    
    return converted_files


class HEICHandler:
    """High-level HEIC file handler."""
    
    def __init__(self, directory: str, recursive: bool = False):
        """
        Initialize HEIC handler.
        
        Args:
            directory: Base directory to work in
            recursive: Search recursively
        """
        self.directory = directory
        self.recursive = recursive
        self.heic_files = []
    
    def scan(self) -> int:
        """
        Scan directory for HEIC files.
        
        Returns:
            Number of HEIC files found
        """
        self.heic_files = find_heic_files(self.directory, self.recursive)
        return len(self.heic_files)
    
    def prompt_and_convert(self) -> List[str]:
        """
        Prompt user to convert HEIC files and perform conversion.
        
        Returns:
            List of converted JPG file paths
        """
        if not self.heic_files:
            return []
        
        print(f"\nFound {len(self.heic_files)} HEIC files.")
        
        # Prompt user
        while True:
            response = input("Convert HEIC files to JPG? [y/n]: ").lower().strip()
            if response in ('y', 'yes'):
                print("Converting HEIC files...")
                converted = batch_convert_heic(
                    self.heic_files, 
                    output_dir=self.directory,
                    move_originals=True
                )
                return converted
            elif response in ('n', 'no'):
                print("Skipping HEIC conversion.")
                return []
            else:
                print("Please enter 'y' or 'n'")
