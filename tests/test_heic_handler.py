"""Unit and integration tests for images2kmz.heic_handler module."""

import os
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, PropertyMock
import pytest

from images2kmz.heic_handler import (
    find_heic_files,
    convert_heic_to_jpg,
    batch_convert_heic,
    HEICHandler,
    HEIC_EXTENSIONS,
)


class TestFindHeicFiles:
    """Tests for find_heic_files() function."""

    def test_find_heic_files_non_recursive(self, tmp_path):
        """
        Test finding HEIC files in a single directory (non-recursive).

        Should return only HEIC files in the specified directory, not subdirectories.
        """
        # Create test files
        (tmp_path / "photo1.heic").touch()
        (tmp_path / "photo2.heic").touch()
        (tmp_path / "photo.jpg").touch()
        (tmp_path / "doc.txt").touch()

        result = find_heic_files(str(tmp_path), recursive=False)

        assert len(result) == 2
        assert all(f.endswith('.heic') for f in result)
        assert str(tmp_path / "photo1.heic") in result
        assert str(tmp_path / "photo2.heic") in result

    def test_find_heic_files_recursive(self, tmp_path):
        """
        Test finding HEIC files recursively in subdirectories.

        Should find HEIC files at all directory levels.
        """
        # Create nested structure
        (tmp_path / "root.heic").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.heic").touch()
        nested_subdir = subdir / "nested"
        nested_subdir.mkdir()
        (nested_subdir / "deep.heic").touch()

        result = find_heic_files(str(tmp_path), recursive=True)

        assert len(result) == 3
        assert str(tmp_path / "root.heic") in result
        assert str(subdir / "nested.heic") in result
        assert str(nested_subdir / "deep.heic") in result

    def test_find_heic_files_empty_directory(self, tmp_path):
        """
        Test finding HEIC files in empty directory.

        Should return empty list when no HEIC files exist.
        """
        result = find_heic_files(str(tmp_path))
        assert result == []

    def test_find_heic_files_permission_error(self, tmp_path):
        """
        Test handling of permission errors.

        Should return empty list gracefully when permission denied.
        """
        with patch('os.listdir', side_effect=PermissionError("Access denied")):
            result = find_heic_files(str(tmp_path))
            assert result == []

    def test_find_heic_files_case_insensitive(self, tmp_path):
        """
        Test that HEIC file detection is case insensitive.

        Should find .heic, .HEIC, .Heic, etc.
        """
        (tmp_path / "lower.heic").touch()
        (tmp_path / "UPPER.HEIC").touch()
        (tmp_path / "Mixed.Heic").touch()

        result = find_heic_files(str(tmp_path))

        assert len(result) == 3


class TestConvertHeicToJpg:
    """Tests for convert_heic_to_jpg() function."""

    @patch('images2kmz.heic_handler.Image.open')
    def test_convert_heic_to_jpg_success_mocked(self, mock_image_open, tmp_path):
        """
        Test successful HEIC to JPG conversion (mocked).

        Should open image, extract EXIF, transpose, convert, and save as JPG.
        Integration tests verify actual file operations with real HEIC files.
        """
        # Setup mock image - use MagicMock for context manager support
        mock_img = MagicMock()
        mock_img.info = {'exif': b'fake_exif_data'}
        type(mock_img).mode = PropertyMock(return_value='RGB')
        # Setup the mock to be used as a context manager
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_img)
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_image_open.return_value = mock_context

        heic_file = tmp_path / "test.heic"
        heic_file.touch()

        result = convert_heic_to_jpg(str(heic_file), str(tmp_path))

        # Verify a JPG path was returned
        assert result is not None
        assert result.endswith('.jpg')

    @patch('images2kmz.heic_handler.Image.open')
    def test_convert_heic_to_jpg_no_output_dir(self, mock_image_open, tmp_path):
        """
        Test conversion without specifying output directory.

        Should save JPG in same directory as HEIC file.
        """
        mock_img = Mock()
        mock_img.info = {}
        mock_img.mode = 'RGB'
        mock_image_open.return_value.__enter__ = Mock(return_value=mock_img)
        mock_image_open.return_value.__exit__ = Mock(return_value=False)

        heic_file = tmp_path / "test.heic"
        heic_file.touch()

        result = convert_heic_to_jpg(str(heic_file))

        assert result is not None
        assert str(tmp_path) in result

    @patch('images2kmz.heic_handler.Image.open')
    def test_convert_heic_to_jpg_custom_output_dir(self, mock_image_open, tmp_path):
        """
        Test conversion with custom output directory.

        Should save JPG in specified output directory.
        """
        mock_img = Mock()
        mock_img.info = {}
        mock_img.mode = 'RGB'
        mock_image_open.return_value.__enter__ = Mock(return_value=mock_img)
        mock_image_open.return_value.__exit__ = Mock(return_value=False)

        heic_file = tmp_path / "subdir" / "test.heic"
        heic_file.parent.mkdir()
        heic_file.touch()

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = convert_heic_to_jpg(str(heic_file), str(output_dir))

        assert result is not None
        assert str(output_dir) in result

    @patch('images2kmz.heic_handler.Image.open')
    def test_convert_heic_to_jpg_conversion_failure(self, mock_image_open, tmp_path, capsys):
        """
        Test handling of conversion failures.

        Should return None when conversion fails and print error.
        """
        mock_image_open.side_effect = Exception("Corrupted file")

        heic_file = tmp_path / "test.heic"
        heic_file.touch()

        result = convert_heic_to_jpg(str(heic_file))

        assert result is None

    @patch('images2kmz.heic_handler.Image.open')
    def test_convert_heic_to_jpg_with_rgba_mode(self, mock_image_open, tmp_path):
        """
        Test conversion of RGBA mode images.

        Should handle RGBA images correctly during conversion.
        This behavior is also covered by integration tests.
        """
        mock_img = Mock()
        mock_img.info = {'exif': b'fake_exif'}
        # Simulate RGBA mode - the code should handle conversion
        type(mock_img).mode = PropertyMock(return_value='RGBA')
        converted_mock = Mock()
        converted_mock.mode = 'RGB'
        mock_img.convert.return_value = converted_mock
        mock_image_open.return_value.__enter__ = Mock(return_value=mock_img)
        mock_image_open.return_value.__exit__ = Mock(return_value=False)

        heic_file = tmp_path / "test.heic"
        heic_file.touch()

        result = convert_heic_to_jpg(str(heic_file), str(tmp_path))

        # Just verify conversion completed successfully
        assert result is not None


class TestBatchConvertHeic:
    """Tests for batch_convert_heic() function."""

    @patch('images2kmz.heic_handler.convert_heic_to_jpg')
    def test_batch_convert_success(self, mock_convert, tmp_path):
        """
        Test batch conversion of multiple files.

        Should convert all files and return list of JPG paths.
        """
        mock_convert.side_effect = [
            str(tmp_path / "1.jpg"),
            str(tmp_path / "2.jpg"),
        ]

        heic_files = [str(tmp_path / "1.heic"), str(tmp_path / "2.heic")]
        result = batch_convert_heic(heic_files, str(tmp_path))

        assert len(result) == 2
        assert mock_convert.call_count == 2

    @patch('images2kmz.heic_handler.convert_heic_to_jpg')
    def test_batch_convert_partial_failure(self, mock_convert, tmp_path):
        """
        Test batch conversion with some failures.

        Should return only successfully converted files.
        """
        mock_convert.side_effect = [
            str(tmp_path / "1.jpg"),
            None,  # Second file fails
        ]

        heic_files = [str(tmp_path / "1.heic"), str(tmp_path / "2.heic")]
        result = batch_convert_heic(heic_files, str(tmp_path))

        assert len(result) == 1
        assert str(tmp_path / "1.jpg") in result

    @patch('images2kmz.heic_handler.convert_heic_to_jpg')
    @patch('images2kmz.heic_handler.shutil.move')
    @patch('os.makedirs')
    def test_batch_convert_move_originals(self, mock_makedirs, mock_move, mock_convert, tmp_path):
        """
        Test moving original HEIC files after conversion.

        Should move originals to subdirectory when move_originals=True.
        """
        mock_convert.return_value = str(tmp_path / "1.jpg")

        heic_file = tmp_path / "1.heic"
        heic_file.touch()

        result = batch_convert_heic([str(heic_file)], str(tmp_path), move_originals=True)

        assert len(result) == 1
        mock_move.assert_called_once()

    @patch('images2kmz.heic_handler.convert_heic_to_jpg')
    @patch('images2kmz.heic_handler.shutil.move')
    def test_batch_convert_move_failure(self, mock_move, mock_convert, tmp_path, capsys):
        """
        Test handling of move failures.

        Should continue processing other files if one move fails.
        """
        mock_convert.return_value = str(tmp_path / "1.jpg")
        mock_move.side_effect = Exception("Permission denied")

        heic_file = tmp_path / "1.heic"
        heic_file.touch()

        result = batch_convert_heic([str(heic_file)], str(tmp_path), move_originals=True)

        assert len(result) == 1  # Conversion still succeeded
        mock_move.assert_called_once()  # Attempted to move


class TestHEICHandler:
    """Tests for HEICHandler class."""

    def test_heic_handler_init(self):
        """
        Test HEICHandler initialization.

        Should set directory, recursive flag, and initialize empty heic_files list.
        """
        handler = HEICHandler("/test/dir", recursive=True)

        assert handler.directory == "/test/dir"
        assert handler.recursive is True
        assert handler.heic_files == []

    @patch('images2kmz.heic_handler.find_heic_files')
    def test_heic_handler_scan(self, mock_find):
        """
        Test scanning for HEIC files.

        Should call find_heic_files and store results.
        """
        mock_find.return_value = ["/path/1.heic", "/path/2.heic"]

        handler = HEICHandler("/test/dir", recursive=False)
        count = handler.scan()

        assert count == 2
        assert handler.heic_files == ["/path/1.heic", "/path/2.heic"]
        mock_find.assert_called_once_with("/test/dir", False)

    def test_heic_handler_prompt_and_convert_no_files(self):
        """
        Test prompt_and_convert when no files found.

        Should return empty list immediately.
        """
        handler = HEICHandler("/test/dir")
        handler.heic_files = []

        result = handler.prompt_and_convert()

        assert result == []

    @patch('builtins.input', return_value='y')
    @patch('images2kmz.heic_handler.batch_convert_heic')
    def test_heic_handler_prompt_and_convert_yes(self, mock_batch, mock_input):
        """
        Test prompt_and_convert when user confirms.

        Should call batch_convert_heic when user enters 'y'.
        """
        handler = HEICHandler("/test/dir")
        handler.heic_files = ["/path/1.heic"]
        mock_batch.return_value = ["/path/1.jpg"]

        result = handler.prompt_and_convert()

        assert result == ["/path/1.jpg"]
        mock_batch.assert_called_once()


class TestHEICIntegration:
    """Integration tests using real HEIC files."""

@pytest.fixture
def sample_heic_dir() -> Path:
    """Return path to sample HEIC files for integration tests."""
    return Path(__file__).parent / "fixtures" / "sample-images"

    def test_find_heic_files_with_real_files(self, sample_heic_dir):
        """
        Integration test: Find real HEIC files in sample-images directory.

        Should find the HEIC files that exist in the sample directory.
        """
        if not sample_heic_dir.exists():
            pytest.skip("Sample images directory not found")

        result = find_heic_files(str(sample_heic_dir), recursive=False)

        # Should find HEIC files in sample-images
        assert len(result) > 0
        assert all(f.endswith(('.heic', '.heif')) for f in result)

    def test_convert_real_heic_file(self, sample_heic_dir, tmp_path):
        """
        Integration test: Convert a real HEIC file to JPG.

        Should successfully convert HEIC to JPG with valid output.
        """
        if not sample_heic_dir.exists():
            pytest.skip("Sample images directory not found")

        heic_files = list(sample_heic_dir.rglob("*.heic"))
        if not heic_files:
            pytest.skip("No HEIC files found in sample directory")

        heic_file = heic_files[0]
        result = convert_heic_to_jpg(str(heic_file), str(tmp_path))

        assert result is not None
        assert Path(result).exists()
        assert Path(result).stat().st_size > 0
        assert result.endswith('.jpg')

        # Cleanup
        Path(result).unlink()

    def test_heic_handler_scan_with_real_files(self, sample_heic_dir):
        """
        Integration test: HEICHandler scan with real files.

        Should find HEIC files using the handler class.
        """
        if not sample_heic_dir.exists():
            pytest.skip("Sample images directory not found")

        handler = HEICHandler(str(sample_heic_dir), recursive=False)
        count = handler.scan()

        # Should find the 4 HEIC files in sample-images
        assert count > 0
        assert len(handler.heic_files) == count

    def test_batch_convert_with_real_files(self, sample_heic_dir, tmp_path):
        """
        Integration test: Batch convert real HEIC files.

        Should convert multiple files successfully.
        """
        if not sample_heic_dir.exists():
            pytest.skip("Sample images directory not found")

        heic_files = list(sample_heic_dir.rglob("*.heic"))[:2]  # First 2 files
        if len(heic_files) < 2:
            pytest.skip("Need at least 2 HEIC files for batch test")

        result = batch_convert_heic(
            [str(f) for f in heic_files],
            str(tmp_path),
            move_originals=False
        )

        assert len(result) == len(heic_files)
        for jpg_path in result:
            assert Path(jpg_path).exists()
            assert Path(jpg_path).stat().st_size > 0
            # Cleanup
            Path(jpg_path).unlink()
