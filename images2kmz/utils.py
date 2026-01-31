"""Utility functions for images2kmz package."""

import os
from pathlib import Path
from typing import Union


def get_absolute_path(path: Union[str, Path]) -> str:
    """
    Convert a path to an absolute path.
    
    Args:
        path: File or directory path (can be relative or absolute)
        
    Returns:
        Absolute path as string
    """
    return os.path.abspath(os.path.expanduser(str(path)))


def create_file_uri(path: Union[str, Path]) -> str:
    """
    Convert a file path to a file:// URI.
    
    Args:
        path: File path
        
    Returns:
        file:// URI string
    """
    abs_path = get_absolute_path(path)
    # Convert to URI format
    if abs_path.startswith('/'):
        return f'file://{abs_path}'
    else:
        # Windows paths
        return f'file:///{abs_path.replace(os.sep, "/")}'


def ensure_directory_exists(path: Union[str, Path]) -> None:
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
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
