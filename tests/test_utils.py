"""Unit tests for images2kmz.utils module."""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from images2kmz.utils import (
    get_absolute_path,
    create_file_uri,
    ensure_directory_exists,
    format_file_size,
)


class TestGetAbsolutePath:
    """Tests for get_absolute_path() function."""

    def test_get_absolute_path_relative(self, tmp_path, monkeypatch):
        """
        Test that relative paths are converted to absolute paths.

        Given a relative path like './test', should return the full absolute path
        relative to the current working directory.
        """
        # Change to tmp_path to have a predictable base
        monkeypatch.chdir(tmp_path)
        result = get_absolute_path('./test')
        assert result == str(tmp_path / 'test')

    def test_get_absolute_path_home_dir(self):
        """
        Test that home directory expansion works correctly.

        Given a path starting with '~', should expand to the user's home directory.
        Example: '~/documents' → '/Users/username/documents'
        """
        result = get_absolute_path('~/documents')
        expected = os.path.expanduser('~/documents')
        assert result == os.path.abspath(expected)

    def test_get_absolute_path_already_absolute(self, tmp_path):
        """
        Test that absolute paths are returned unchanged.

        Given an already absolute path, should return it as-is without modification.
        """
        abs_path = str(tmp_path / 'test')
        result = get_absolute_path(abs_path)
        assert result == abs_path

    def test_get_absolute_path_parent_dir(self, tmp_path):
        """
        Test handling of paths with parent directory references.

        Given a path with '..' components, should resolve them correctly.
        Example: '/a/b/../c' → '/a/c'
        """
        # Create a nested structure
        nested = tmp_path / 'a' / 'b' / 'c'
        nested.mkdir(parents=True)

        # Test path with parent reference
        result = get_absolute_path(str(tmp_path / 'a' / 'b' / '..' / 'c'))
        expected = str(tmp_path / 'a' / 'c')
        assert result == expected

    def test_get_absolute_path_path_object(self, tmp_path):
        """
        Test that Path objects are handled correctly.

        Given a pathlib.Path object, should convert it to absolute path string.
        """
        path_obj = Path('test')
        result = get_absolute_path(path_obj)
        assert isinstance(result, str)
        assert os.path.isabs(result)


class TestCreateFileUri:
    """Tests for create_file_uri() function."""

    def test_create_file_uri_unix_absolute(self):
        """
        Test Unix absolute path to file URI conversion.

        Given a Unix absolute path, should convert to file:///path format.
        Example: '/path/to/file' → 'file:///path/to/file'
        """
        result = create_file_uri('/path/to/file')
        assert result == 'file:///path/to/file'

    @patch('images2kmz.utils.os.sep', '\\\\')
    @patch('images2kmz.utils.os.path.abspath', return_value='C:\\\\path\\\\to\\\\file')
    def test_create_file_uri_windows(self, mock_abspath):
        r"""
        Test Windows path to file URI conversion.

        Given a Windows path, should convert to file:///C:/path format.
        Example: 'C:\path\to\file' → 'file:///C:/path/to/file'
        """
        result = create_file_uri('C:\\\\path\\\\to\\\\file')
        assert result == 'file:///C:/path/to/file'

    def test_create_file_uri_relative(self, tmp_path, monkeypatch):
        """
        Test that relative paths are converted to absolute before URI creation.

        Given a relative path, should first convert to absolute, then to URI.
        """
        monkeypatch.chdir(tmp_path)
        result = create_file_uri('./test')
        assert result.startswith('file:///')
        assert result.endswith('/test')

    def test_create_file_uri_spaces(self):
        """
        Test handling of paths with spaces.

        Given a path containing spaces, should handle them correctly in URI.
        Example: '/path with spaces/file' → 'file:///path with spaces/file'
        """
        result = create_file_uri('/path with spaces/file')
        assert result == 'file:///path with spaces/file'


class TestEnsureDirectoryExists:
    """Tests for ensure_directory_exists() function."""

    def test_ensure_directory_exists_new(self, tmp_path):
        """
        Test creation of a new directory.

        Given a non-existent directory path, should create it successfully.
        """
        new_dir = tmp_path / 'new_directory'
        assert not new_dir.exists()

        ensure_directory_exists(new_dir)

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_directory_exists_existing(self, tmp_path):
        """
        Test that existing directories don't cause errors.

        Given an already existing directory, should not raise an error.
        """
        existing_dir = tmp_path / 'existing'
        existing_dir.mkdir()

        # Should not raise
        ensure_directory_exists(existing_dir)

        # Directory should still exist
        assert existing_dir.exists()

    def test_ensure_directory_exists_nested(self, tmp_path):
        """
        Test creation of nested directory structures.

        Given a path like 'a/b/c', should create all parent directories.
        """
        nested = tmp_path / 'a' / 'b' / 'c'
        assert not nested.exists()

        ensure_directory_exists(nested)

        assert nested.exists()
        assert nested.is_dir()
        # Verify all parents exist
        assert (tmp_path / 'a').exists()
        assert (tmp_path / 'a' / 'b').exists()

    def test_ensure_directory_exists_permission_error(self, tmp_path):
        """
        Test handling of permission errors.

        When permission is denied, should raise appropriate exception.
        """
        # Create a read-only directory
        read_only_dir = tmp_path / 'readonly'
        read_only_dir.mkdir()
        read_only_dir.chmod(0o555)

        try:
            with pytest.raises(PermissionError):
                # Try to create a subdirectory in the read-only directory
                ensure_directory_exists(read_only_dir / 'new_subdir')
        finally:
            # Restore permissions for cleanup
            read_only_dir.chmod(0o755)


class TestFormatFileSize:
    """Tests for format_file_size() function."""

    @pytest.mark.parametrize("size_bytes,expected", [
        (0, "0.0 B"),
        (500, "500.0 B"),
        (1023, "1023.0 B"),
    ])
    def test_format_file_size_bytes(self, size_bytes, expected):
        """
        Test formatting of byte-sized files.

        Files less than 1024 bytes should display in bytes (B).
        """
        result = format_file_size(size_bytes)
        assert result == expected

    @pytest.mark.parametrize("size_bytes,expected", [
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1048575, "1024.0 KB"),
    ])
    def test_format_file_size_kilobytes(self, size_bytes, expected):
        """
        Test formatting of kilobyte-sized files.

        Files between 1-1024 KB should display in kilobytes (KB).
        """
        result = format_file_size(size_bytes)
        assert result == expected

    @pytest.mark.parametrize("size_bytes,expected", [
        (1048576, "1.0 MB"),
        (5242880, "5.0 MB"),
        (1073741823, "1024.0 MB"),
    ])
    def test_format_file_size_megabytes(self, size_bytes, expected):
        """
        Test formatting of megabyte-sized files.

        Files between 1-1024 MB should display in megabytes (MB).
        """
        result = format_file_size(size_bytes)
        assert result == expected

    @pytest.mark.parametrize("size_bytes,expected", [
        (1073741824, "1.0 GB"),
        (2147483648, "2.0 GB"),
        (1099511627775, "1024.0 GB"),
    ])
    def test_format_file_size_gigabytes(self, size_bytes, expected):
        """
        Test formatting of gigabyte-sized files.

        Files between 1-1024 GB should display in gigabytes (GB).
        """
        result = format_file_size(size_bytes)
        assert result == expected

    def test_format_file_size_terabytes(self):
        """
        Test formatting of terabyte-sized files.

        Files >= 1024 GB should display in terabytes (TB).
        """
        # 1 TB
        result = format_file_size(1099511627776)
        assert result == "1.0 TB"

        # 2 TB
        result = format_file_size(2199023255552)
        assert result == "2.0 TB"

    def test_format_file_size_exact_boundary(self):
        """
        Test exact boundary values.

        Test that 1024 bytes rounds correctly to 1.0 KB.
        """
        # Exact boundary: 1024 bytes = 1.0 KB
        result = format_file_size(1024)
        assert result == "1.0 KB"

        # Another boundary: 1024 KB = 1.0 MB
        result = format_file_size(1048576)
        assert result == "1.0 MB"
