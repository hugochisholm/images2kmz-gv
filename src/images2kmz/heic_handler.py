from __future__ import annotations

"""HEIC file detection and conversion to JPEG."""

import shutil
from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener
from rich.console import Console

console = Console()

# Initialize HEIC support
register_heif_opener()

HEIC_EXTENSIONS = ('.heic', '.heif')


def find_heic_files(directory: str, recursive: bool = False) -> list[str]:
    """
    Find all HEIC/HEIF files in a directory.
    
    Args:
        directory: Directory to search
        recursive: Search subdirectories recursively
        
    Returns:
        List of absolute paths to HEIC files
    """
    heic_files = []
    dir_path = Path(directory)

    if recursive:
        for file_path in dir_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in HEIC_EXTENSIONS:
                heic_files.append(str(file_path))
    else:
        try:
            for file_path in dir_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in HEIC_EXTENSIONS:
                    heic_files.append(str(file_path))
        except (PermissionError, FileNotFoundError):
            pass

    return sorted(heic_files)


def convert_heic_to_jpg(heic_path: str, output_dir: str | None = None) -> str | None:
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
        heic_path_obj = Path(heic_path)
        if output_dir is None:
            output_dir_path = heic_path_obj.parent
        else:
            output_dir_path = Path(output_dir)

        # Create output filename (replace extension with .jpg)
        base_name = heic_path_obj.stem
        jpg_path = str(output_dir_path / f"{base_name}.jpg")
        
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
        console.print(f"[red]Error converting {heic_path}: {e}[/red]")
        return None


def batch_convert_heic(heic_files: list[str], output_dir: str | None = None, 
                       move_originals: bool = False, originals_dir: str = "HEIC originals") -> list[str]:
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
            console.print(f"  [green]✓[/green] {Path(heic_path).name} → {Path(jpg_path).name}")
        else:
            console.print(f"  [red]✗ Failed: {Path(heic_path).name}[/red]")
    
    # Move original HEIC files if requested
    if move_originals and converted_files:
        # Determine where to create the originals directory
        if heic_files:
            first_file_dir = Path(heic_files[0]).parent
            originals_path = first_file_dir / originals_dir

            # Create directory
            originals_path.mkdir(parents=True, exist_ok=True)

            # Move files
            for heic_path in heic_files:
                try:
                    dest_path = originals_path / Path(heic_path).name
                    shutil.move(heic_path, str(dest_path))
                except Exception as e:
                    console.print(f"  [yellow]Warning: Could not move {Path(heic_path).name}: {e}[/yellow]")

            console.print(f"[blue]Moved {len(heic_files)} original HEIC files to '{originals_dir}/'[/blue]")
    
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
    
    def prompt_and_convert(self) -> list[str]:
        """
        Prompt user to convert HEIC files and perform conversion.
        
        Returns:
            List of converted JPG file paths
        """
        if not self.heic_files:
            return []
        
        console.print(f"\n[blue]Found {len(self.heic_files)} HEIC files.[/blue]")
        
        # Prompt user
        while True:
            response = input("Convert HEIC files to JPG? [y/n]: ").lower().strip()
            if response in ('y', 'yes'):
                console.print("[blue]Converting HEIC files...[/blue]")
                converted = batch_convert_heic(
                    self.heic_files, 
                    output_dir=self.directory,
                    move_originals=True
                )
                return converted
            elif response in ('n', 'no'):
                console.print("[yellow]Skipping HEIC conversion.[/yellow]")
                return []
            else:
                console.print("[yellow]Please enter 'y' or 'n'[/yellow]")
