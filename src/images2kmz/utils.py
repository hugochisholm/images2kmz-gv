from __future__ import annotations

"""Utility functions for images2kmz package."""

from pathlib import Path, PureWindowsPath



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
    Convert a file path to a file:// URI for Windows.
    
    Args:
        path: File path
        
    Returns:
        file:// URI string
    """
    abs_path = get_absolute_path(path)
    
    # Handle UNC network paths (\\server\share)
    if abs_path.startswith('\\\\'):
        # UNC paths need 2 slashes: file://server/share (no leading slash)
        return f"file://{abs_path.lstrip(chr(92)).replace(chr(92), '/')}"
    
    # Handle regular Windows paths (C:\path)
    if '\\' in abs_path or (len(abs_path) > 1 and abs_path[1] == ':'):
        win_path = PureWindowsPath(abs_path)
        return f"file:///{win_path}"
    
    # Unix-style paths
    # Strip leading slash since file:/// already includes the root separator
    return f"file:///{abs_path.lstrip('/')}"


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
