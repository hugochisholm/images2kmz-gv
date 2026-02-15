from __future__ import annotations

"""Utility functions for images2kmz package."""

from pathlib import Path



def get_absolute_path(path: str | Path) -> str:
    """
    Convert a path to an absolute path.
    
    Args:
        path: File or directory path (can be relative or absolute)
        
    Returns:
        Absolute path as string
    """
    return str(Path(path).expanduser().resolve())


def create_file_uri(path: str | Path) -> str:
    """
    Convert a file path to a file:// URI.
    
    Args:
        path: File path
        
    Returns:
        file:// URI string
    """
    abs_path = get_absolute_path(path)
    # Convert to URI format (handles both Unix and Windows paths)
    return f'file://{abs_path}'


def ensure_directory_exists(path: str | Path) -> None:
    """
    Create directory if it doesn't exist.
    
    Args:
        path: Directory path to create
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., "2.4 MB")
    """
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"
