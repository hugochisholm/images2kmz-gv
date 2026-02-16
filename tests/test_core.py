"""Unit tests for images2kmz.core module."""

import os
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from images2kmz.core import KMZGenerator
from images2kmz.image_processor import GPSData, create_thumbnail


class TestKMZGeneratorInit:
    """Tests for KMZGenerator initialization."""

    def test_init_default_parameters(self):
        """
        Test initialization with default parameters.

        Should use default thumbnail_size (800, 600) and None callback.
        Temp directory is None until context manager is entered.
        """
        generator = KMZGenerator('/test/output.kmz')

        assert generator.output_path == '/test/output.kmz'
        assert generator.thumbnail_size == (800, 600)
        assert generator.progress_callback is None
        assert generator.stats == {'photos_added': 0, 'total_size': 0}
        assert generator._temp_dir is None

    def test_init_custom_parameters(self):
        """
        Test initialization with custom parameters.

        Should store all custom values correctly.
        """
        callback = lambda x, y, z: None
        generator = KMZGenerator(
            '/test/output.kmz',
            thumbnail_size=(400, 300),
            progress_callback=callback
        )
        
        assert generator.output_path == '/test/output.kmz'
        assert generator.thumbnail_size == (400, 300)
        assert generator.progress_callback is callback

    @patch('images2kmz.core.simplekml.Kml')
    def test_init_creates_kml_instance(self, mock_kml_class):
        """
        Test that Kml instance is created during initialization.

        Should call simplekml.Kml() to create KML structure.
        """
        mock_kml = Mock()
        mock_kml_class.return_value = mock_kml
        
        with KMZGenerator('/test.kmz') as generator:
            mock_kml_class.assert_called_once()
            assert generator.kml is mock_kml

    def test_init_output_path_stored_as_is(self):
        """
        Test that output_path is stored without conversion.

        Path conversion should happen in save() method.
        """
        generator = KMZGenerator('relative/path.kmz')
        assert generator.output_path == 'relative/path.kmz'


class TestKMZGeneratorAddPhoto:
    """Tests for add_photo() method."""

    def test_add_photo_raises_error_without_context_manager(self):
        """
        Test that add_photo raises error when used without context manager.

        Should raise RuntimeError if temp directory is not initialized.
        """
        mock_kml = Mock()

        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            generator = KMZGenerator('/test.kmz')  # No context manager!
            gps = GPSData(49.44, -95.41)

            with pytest.raises(RuntimeError):
                generator.add_photo('/photo.jpg', gps, b'thumb')

    def test_add_photo_basic(self):
        """
        Test basic photo addition with GPS data.

        Should create placemark with correct coordinates and description.
        Must use context manager to initialize temp directory.
        """
        mock_kml = Mock()
        mock_kml.addfile.return_value = 'files/thumb_123.jpg'
        mock_point = Mock()
        mock_kml.newpoint.return_value = mock_point

        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                gps = GPSData(latitude=49.441272, longitude=-95.405539)
                thumbnail = b'fake_thumbnail_bytes'

                generator.add_photo('/path/to/photo.jpg', gps, thumbnail, name='Test Photo')

                # Verify placemark created
                mock_kml.newpoint.assert_called_once()
                call_args = mock_kml.newpoint.call_args
                assert call_args[1]['name'] == 'Test Photo'
                assert call_args[1]['coords'] == [(-95.405539, 49.441272)]

                # Verify description was set
                assert mock_point.description is not None
                assert 'files/thumb_123.jpg' in mock_point.description

                # Verify stats
                assert generator.stats['photos_added'] == 1
                assert generator.stats['total_size'] == len(thumbnail)

    def test_add_photo_with_altitude(self):
        """
        Test photo addition with altitude.

        Should include altitude in coordinates tuple.
        Must use context manager to initialize temp directory.
        """
        mock_kml = Mock()
        mock_kml.addfile.return_value = 'files/thumb.jpg'
        mock_point = Mock()
        mock_kml.newpoint.return_value = mock_point

        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                gps = GPSData(latitude=49.441272, longitude=-95.405539, altitude=100.5)

                generator.add_photo('/photo.jpg', gps, b'thumb')

                call_args = mock_kml.newpoint.call_args
                # Altitude should be included: (lon, lat, alt)
                assert call_args[1]['coords'] == [(-95.405539, 49.441272, 100.5)]

    def test_add_photo_default_name(self):
        """
        Test that filename is used when name not provided.

        Should use basename of photo_path as placemark name.
        Must use context manager to initialize temp directory.
        """
        mock_kml = Mock()
        mock_kml.addfile.return_value = 'files/thumb.jpg'
        mock_point = Mock()
        mock_kml.newpoint.return_value = mock_point
        
        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                gps = GPSData(49.44, -95.41)
                
                generator.add_photo('/path/to/my_photo.jpg', gps, b'thumb')
        
        call_args = mock_kml.newpoint.call_args
        assert call_args[1]['name'] == 'my_photo.jpg'

    def test_add_photo_with_description(self):
        """
        Test photo with custom description text.

        Should format description and replace ' - ' with <br/>.
        Must use context manager to initialize temp directory.
        """
        mock_kml = Mock()
        mock_kml.addfile.return_value = 'files/thumb.jpg'
        mock_point = Mock()
        mock_kml.newpoint.return_value = mock_point
        
        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                gps = GPSData(49.44, -95.41)
                description = 'Point A - Location B - Date C'
                
                generator.add_photo('/photo.jpg', gps, b'thumb', description_text=description)
        
        # Verify description contains formatted text
        assert mock_point.description is not None
        assert 'Point A' in mock_point.description
        assert '<br/>' in mock_point.description

    def test_add_photo_with_bearing(self):
        """
        Test photo with compass bearing data.

        Should display bearing in description.
        Must use context manager to initialize temp directory.
        """
        mock_kml = Mock()
        mock_kml.addfile.return_value = 'files/thumb.jpg'
        mock_point = Mock()
        mock_kml.newpoint.return_value = mock_point
        
        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                gps = GPSData(49.44, -95.41)
                bearing = {'raw_text': '45° NE'}
                
                generator.add_photo('/photo.jpg', gps, b'thumb', bearing=bearing)
        
        # Verify bearing in description
        assert mock_point.description is not None
        assert '45° NE' in mock_point.description
        assert 'Direction:' in mock_point.description

    def test_add_photo_with_bearing_sets_icon_style(self):
        """
        Test photo with bearing sets directional icon and rotation.

        Should set track-0.png icon with heading rotation.
        Must use context manager to initialize temp directory.
        """
        mock_kml = Mock()
        mock_kml.addfile.return_value = 'files/thumb.jpg'
        mock_point = Mock()
        mock_kml.newpoint.return_value = mock_point
        
        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                gps = GPSData(49.44, -95.41)
                bearing = {'azimuth': 45, 'compass': 'NE', 'raw_text': 'NE 45°'}
                
                generator.add_photo('/photo.jpg', gps, b'thumb', bearing=bearing)
        
        # Verify icon style is set correctly
        assert mock_point.style.iconstyle.icon.href == 'http://earth.google.com/images/kml-icons/track-directional/track-0.png'
        assert mock_point.style.iconstyle.heading == 45

    def test_add_photo_without_bearing_sets_none_icon(self):
        """
        Test photo without bearing sets non-directional icon.

        Should set track-none.png icon without rotation.
        Must use context manager to initialize temp directory.
        """
        mock_kml = Mock()
        mock_kml.addfile.return_value = 'files/thumb.jpg'
        mock_point = Mock()
        mock_kml.newpoint.return_value = mock_point
        
        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                gps = GPSData(49.44, -95.41)
                
                generator.add_photo('/photo.jpg', gps, b'thumb')
        
        # Verify icon style is set correctly
        assert mock_point.style.iconstyle.icon.href == 'http://earth.google.com/images/kml-icons/track-directional/track-none.png'

    def test_add_photo_icon_scale(self):
        """
        Test that icon scale is set to 1.4.

        Icons should be scaled for visibility.
        Must use context manager to initialize temp directory.
        """
        mock_kml = Mock()
        mock_kml.addfile.return_value = 'files/thumb.jpg'
        mock_point = Mock()
        mock_kml.newpoint.return_value = mock_point
        
        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                gps = GPSData(49.44, -95.41)
                
                generator.add_photo('/photo.jpg', gps, b'thumb')
        
        # Verify icon scale
        assert mock_point.style.iconstyle.scale == 1.4

    def test_add_photo_temp_file_creation(self):
        """
        Test temporary file creation for thumbnails.

        Should create temp file within TemporaryDirectory.
        Must use context manager to initialize temp directory.
        """
        mock_kml = Mock()
        mock_kml.addfile.return_value = 'files/thumb.jpg'
        mock_point = Mock()
        mock_kml.newpoint.return_value = mock_point

        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                gps = GPSData(49.44, -95.41)
                thumbnail = b'thumbnail_data'

                generator.add_photo('/photo.jpg', gps, thumbnail)

                # Verify temp directory is set up
                assert generator._temp_dir is not None
                assert generator._temp_dir.name is not None

                # Verify thumbnail file was written to temp directory
                temp_path = Path(generator._temp_dir.name)
                thumb_files = list(temp_path.glob('thumb_*.jpg'))
                assert len(thumb_files) == 1

                # Verify thumbnail content
                assert thumb_files[0].read_bytes() == thumbnail

    def test_add_photo_creates_file_uri(self):
        """
        Test that file:// URI to original photo is included.

        Description should contain link to original photo.
        Must use context manager to initialize temp directory.
        """
        mock_kml = Mock()
        mock_kml.addfile.return_value = 'files/thumb.jpg'
        mock_point = Mock()
        mock_kml.newpoint.return_value = mock_point

        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                gps = GPSData(49.44, -95.41)

                generator.add_photo('/path/to/original.jpg', gps, b'thumb')

                # Verify file URI in description
                assert mock_point.description is not None
                assert 'file://' in mock_point.description
                assert 'original.jpg' in mock_point.description

    def test_add_photo_stats_tracking(self):
        """
        Test that stats are tracked correctly.

        Should increment photos_added and accumulate total_size.
        """
        mock_kml = Mock()
        mock_kml.addfile.return_value = 'files/thumb.jpg'
        mock_point = Mock()
        mock_kml.newpoint.return_value = mock_point
        
        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                gps = GPSData(49.44, -95.41)
                
                # Add three photos
                generator.add_photo('/photo1.jpg', gps, b'thumb1')  # 6 bytes
                generator.add_photo('/photo2.jpg', gps, b'thumb22')  # 7 bytes
                generator.add_photo('/photo3.jpg', gps, b'thumb333')  # 8 bytes
            
                assert generator.stats['photos_added'] == 3
                assert generator.stats['total_size'] == 21  # 6 + 7 + 8

    def test_add_photo_coordinates_format(self):
        """
        Test coordinate formatting in description.

        Should display coordinates with 6 decimal places.
        """
        mock_kml = Mock()
        mock_kml.addfile.return_value = 'files/thumb.jpg'
        mock_point = Mock()
        mock_kml.newpoint.return_value = mock_point
        
        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                gps = GPSData(latitude=49.441272, longitude=-95.405539)
                
                generator.add_photo('/photo.jpg', gps, b'thumb')
        
                # Verify coordinates in description with 6 decimal places
                assert mock_point.description is not None
                assert '49.441272' in mock_point.description
                assert '-95.405539' in mock_point.description


class TestKMZGeneratorSave:
    """Tests for save() method."""

    def test_save_success(self):
        """
        Test successful KMZ save.

        Should call savekmz and return absolute path.
        """
        mock_kml = Mock()

        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test/output.kmz') as generator:
                with patch('images2kmz.core.Path.exists', return_value=True):
                    with patch('images2kmz.core.Path.is_absolute', return_value=True):
                        with patch('images2kmz.core.Path.mkdir'):
                            with patch('images2kmz.core.Path.stat') as mock_stat:
                                mock_stat.return_value.st_size = 1024
                                result = generator.save()

                # Verify savekmz called
                mock_kml.savekmz.assert_called_once_with('/test/output.kmz')

                # Verify absolute path returned
                assert result is not None
                assert Path(result).is_absolute()

    @patch('images2kmz.core.Path.mkdir')
    def test_save_creates_directory(self, mock_mkdir):
        """
        Test directory creation for output path.

        Should create parent directories if they don't exist.
        """
        mock_kml = Mock()

        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/output/subdir/test.kmz') as generator:
                with patch('images2kmz.core.Path.stat') as mock_stat:
                    mock_stat.return_value.st_size = 1024
                    generator.save()

                # Verify directory created
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_save_temp_file_cleanup(self):
        """
        Test temporary file cleanup after save.

        Should clean up temporary directory after save.
        """
        mock_kml = Mock()

        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                # Verify temp directory is set up
                assert generator._temp_dir is not None
                temp_dir_name = generator._temp_dir.name

                # Save should trigger cleanup
                with patch.object(generator, 'cleanup') as mock_cleanup:
                    with patch('images2kmz.core.Path.stat') as mock_stat:
                        mock_stat.return_value.st_size = 1024
                        generator.save()
                    mock_cleanup.assert_called_once()

    def test_save_cleanup_on_failure(self):
        """
        Test cleanup occurs even when save fails.

        Should clean up temp directory even if savekmz raises exception.
        """
        mock_kml = Mock()
        mock_kml.savekmz.side_effect = Exception("Save failed")

        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                # Verify temp directory is set up
                assert generator._temp_dir is not None

                with patch.object(generator, 'cleanup') as mock_cleanup:
                    with pytest.raises(Exception, match="Save failed"):
                        generator.save()

                    # Verify cleanup still happened
                    mock_cleanup.assert_called_once()

    @patch('images2kmz.core.Path.mkdir')
    def test_save_no_directory_needed(self, mock_mkdir):
        """
        Test save when no directory creation needed.

        Current directory output shouldn't call mkdir.
        """
        mock_kml = Mock()

        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('test.kmz') as generator:
                with patch('images2kmz.core.Path.stat') as mock_stat:
                    mock_stat.return_value.st_size = 1024
                    generator.save()

                # Should still call mkdir with exist_ok=True (which handles existing/current dir)
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('images2kmz.core.Path.mkdir')
    def test_save_existing_directory(self, mock_mkdir):
        """
        Test save when directory already exists.

        Should call mkdir with exist_ok=True (handles existing directory).
        """
        mock_kml = Mock()

        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/existing/dir/test.kmz') as generator:
                with patch('images2kmz.core.Path.stat') as mock_stat:
                    mock_stat.return_value.st_size = 1024
                    generator.save()

                # Should call mkdir with exist_ok=True
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('images2kmz.core.Path.unlink')
    def test_save_cleanup_handles_errors(self, mock_unlink):
        """
        Test cleanup handles errors gracefully.

        Should continue even if cleanup raises exception.
        """
        mock_kml = Mock()

        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                # Verify temp directory is set up
                assert generator._temp_dir is not None

                # Mock cleanup to raise an exception
                with patch.object(generator._temp_dir, 'cleanup', side_effect=PermissionError("Access denied")):
                    with patch('images2kmz.core.Path.stat') as mock_stat:
                        mock_stat.return_value.st_size = 1024
                        # Should not raise even if cleanup fails
                        result = generator.save()
                        # Result should still be returned (save succeeded even if cleanup failed)
                        assert result is not None


class TestKMZGeneratorStats:
    """Tests for statistics methods."""

    def test_get_stats_returns_copy(self):
        """
        Test that get_stats returns a copy.

        Modifying returned dict should not affect internal stats.
        """
        mock_kml = Mock()
        
        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                generator.stats = {'photos_added': 5, 'total_size': 1000}
                
                stats = generator.get_stats()
                stats['photos_added'] = 999  # Modify returned dict
                
                # Original should be unchanged
                assert generator.stats['photos_added'] == 5

    @patch('images2kmz.core.Path.exists')
    @patch('images2kmz.core.Path.stat')
    def test_get_file_size_exists(self, mock_stat, mock_exists):
        """
        Test getting file size when file exists.

        Should return size in bytes.
        """
        mock_exists.return_value = True
        mock_stat_result = Mock()
        mock_stat_result.st_size = 2621440  # 2.5 MB in bytes
        mock_stat.return_value = mock_stat_result
        
        mock_kml = Mock()
        
        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                size = generator.get_file_size()
        
                assert size == 2621440  # 2.5 MB in bytes

    @patch('images2kmz.core.Path.exists')
    def test_get_file_size_not_exists(self, mock_exists):
        """
        Test getting file size when file doesn't exist.

        Should return None.
        """
        mock_exists.return_value = False
        
        mock_kml = Mock()
        
        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                size = generator.get_file_size()
        
                assert size is None


class TestKMZGeneratorFormattedSize:
    """Tests for formatted file size methods."""

    def test_get_formatted_file_size_success(self):
        """
        Test formatted size when file exists.

        Should return human-readable size string.
        """
        mock_kml = Mock()
        
        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                with patch.object(generator, 'get_file_size', return_value=1024*1024*2.5):
                    formatted = generator.get_formatted_file_size()
        
                    assert formatted == "2.5 MB"

    def test_get_formatted_file_size_none(self):
        """
        Test formatted size when file doesn't exist.

        Should return None.
        """
        mock_kml = Mock()
        
        with patch('images2kmz.core.simplekml.Kml', return_value=mock_kml):
            with KMZGenerator('/test.kmz') as generator:
                with patch.object(generator, 'get_file_size', return_value=None):
                    formatted = generator.get_formatted_file_size()
        
                    assert formatted is None


class TestKMZGeneratorIntegration:
    """Integration tests with real images and KMZ generation."""

    def test_integration_create_kmz_with_sample_images(self, tmp_path):
        """
        Integration test: Create actual KMZ with real images.

        Should generate valid KMZ file with embedded thumbnails.
        """
        sample_dir = Path(__file__).parent.parent / "sample-images2"
        
        if not sample_dir.exists():
            pytest.skip("sample-images2 directory not found")
        
        jpg_files = list(sample_dir.glob("*.JPG"))[:2]  # Use first 2 images
        
        if len(jpg_files) < 2:
            pytest.skip("Not enough sample images")
        
        output_path = tmp_path / "test_output.kmz"

        # Create generator and add photos using context manager
        with KMZGenerator(str(output_path), thumbnail_size=(400, 300)) as generator:
            for jpg_file in jpg_files:
                # Get GPS data
                from images2kmz.image_processor import extract_gps_data
                gps = extract_gps_data(str(jpg_file))

                if gps is None:
                    continue  # Skip images without GPS

                # Create thumbnail
                thumbnail = create_thumbnail(str(jpg_file), max_size=(400, 300))

                if thumbnail:
                    generator.add_photo(
                        str(jpg_file),
                        gps,
                        thumbnail,
                        name=jpg_file.stem
                    )

            # Save KMZ
            result_path = generator.save()

            # Verify file created
            assert Path(result_path).exists()
            assert output_path.exists()
            assert output_path.stat().st_size > 0

            # Verify it's a valid ZIP/KMZ
            with zipfile.ZipFile(output_path, 'r') as kmz:
                files = kmz.namelist()
                assert 'doc.kml' in files

                # Should have thumbnail files
                thumbs = [f for f in files if f.startswith('files/') and f.endswith('.jpg')]
                assert len(thumbs) >= 1

    def test_integration_verify_kml_structure(self, tmp_path):
        """
        Integration test: Verify KML structure in generated KMZ.

        Should contain valid KML with placemarks.
        """
        sample_dir = Path(__file__).parent.parent / "sample-images2"
        
        if not sample_dir.exists():
            pytest.skip("sample-images2 directory not found")
        
        jpg_files = list(sample_dir.glob("*.JPG"))
        if not jpg_files:
            pytest.skip("No sample images found")
        
        # Use first image with GPS
        from images2kmz.image_processor import extract_gps_data
        
        test_file = None
        test_gps = None
        for jpg_file in jpg_files:
            gps = extract_gps_data(str(jpg_file))
            if gps:
                test_file = jpg_file
                test_gps = gps
                break
        
        if not test_file:
            pytest.skip("No images with GPS data found")
        
        output_path = tmp_path / "test_structure.kmz"

        # Create KMZ with one photo using context manager
        with KMZGenerator(str(output_path)) as generator:
            thumbnail = create_thumbnail(str(test_file), max_size=(400, 300))

            if thumbnail:
                assert test_gps is not None
                generator.add_photo(
                    str(test_file),
                    test_gps,
                    thumbnail,
                    name="Test Placemark"
                )
                generator.save()

            # Verify KML structure
            with zipfile.ZipFile(output_path, 'r') as kmz:
                with kmz.open('doc.kml') as kml_file:
                    kml_content = kml_file.read().decode('utf-8')

            # Check KML contains expected elements (simplekml adds id attributes)
            assert 'Placemark' in kml_content
            assert '<coordinates>' in kml_content
            assert '</coordinates>' in kml_content
            assert 'Test Placemark' in kml_content
            assert '<description>' in kml_content
            assert '</description>' in kml_content
            assert '<img' in kml_content  # Thumbnail image

    def test_integration_stats_accuracy(self, tmp_path):
        """
        Integration test: Verify stats match actual results.

        Stats should accurately reflect photos added.
        """
        sample_dir = Path(__file__).parent.parent / "sample-images2"
        
        if not sample_dir.exists():
            pytest.skip("sample-images2 directory not found")
        
        jpg_files = list(sample_dir.glob("*.JPG"))[:2]
        
        output_path = tmp_path / "test_stats.kmz"

        from images2kmz.image_processor import extract_gps_data

        photos_added = 0
        total_thumbnail_size = 0

        with KMZGenerator(str(output_path)) as generator:
            for jpg_file in jpg_files:
                gps = extract_gps_data(str(jpg_file))
                if gps:
                    thumbnail = create_thumbnail(str(jpg_file), max_size=(400, 300))
                    if thumbnail:
                        generator.add_photo(str(jpg_file), gps, thumbnail)
                        photos_added += 1
                        total_thumbnail_size += len(thumbnail)

            generator.save()

            # Verify stats
            stats = generator.get_stats()
            assert stats['photos_added'] == photos_added
            assert stats['total_size'] == total_thumbnail_size

            # Verify file size
            file_size = generator.get_file_size()
            assert file_size is not None
            assert file_size > 0

            formatted = generator.get_formatted_file_size()
            assert formatted is not None
            assert 'B' in formatted  # Should contain size unit

    def test_integration_end_to_end(self, tmp_path):
        """
        Integration test: Full workflow from images to KMZ.

        End-to-end test using ImageProcessor and KMZGenerator together.
        """
        sample_dir = Path(__file__).parent.parent / "sample-images2"
        
        if not sample_dir.exists():
            pytest.skip("sample-images2 directory not found")
        
        output_path = tmp_path / "test_e2e.kmz"

        # Step 1: Process images
        from images2kmz.image_processor import ImageProcessor
        processor = ImageProcessor(thumbnail_size=(400, 300))
        processed = processor.process_directory(str(sample_dir), recursive=False)

        if not processed:
            pytest.skip("No processable images found")

        # Step 2: Create KMZ using context manager
        with KMZGenerator(str(output_path)) as generator:
            for item in processed:
                generator.add_photo(
                    item['path'],
                    item['gps'],
                    item['thumbnail'],
                    name=item.get('custom_name', Path(item['path']).name),
                    description_text=item.get('description')
                )

            # Step 3: Save
            result = generator.save()

            # Step 4: Verify
            assert Path(result).exists()
            assert generator.stats['photos_added'] == len(processed)

            # Verify KMZ is valid
            with zipfile.ZipFile(output_path, 'r') as kmz:
                files = kmz.namelist()
                assert 'doc.kml' in files
                thumbs = [f for f in files if f.startswith('files/')]
                assert len(thumbs) == len(processed)
