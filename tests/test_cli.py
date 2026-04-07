"""Tests for images2kmz.cli module."""

import sys
import os
import argparse
from unittest.mock import Mock, patch, MagicMock, call
import pytest
from images2kmz import cli
from images2kmz.cli import (
    create_parser,
    prompt_for_directory,
    run,
    main,
    print_header,
    print_summary
)

class TestCreateParser:
    """Tests for argument parser configuration."""

    def test_create_parser_defaults(self):
        """Test parser with default arguments."""
        parser = create_parser()
        args = parser.parse_args([])
        assert args.input_dir is None
        assert args.output == 'photos.kmz'
        assert args.recursive is False
        assert args.thumbnail_size == [800, 600]
        assert args.no_photo_path is False
        assert args.max_images_per_file == 100

    def test_create_parser_full_options(self):
        """Test parser with all options specified."""
        parser = create_parser()
        cmd_args = [
            '/path/to/photos',
            '-o', 'output.kmz',
            '-r',
            '--thumbnail-size', '1024', '768',
                        '--no-photo-path',
            '--max-images-per-file', '50'
        ]
        args = parser.parse_args(cmd_args)
        assert args.input_dir == '/path/to/photos'
        assert args.output == 'output.kmz'
        assert args.recursive is True
        assert args.thumbnail_size == [1024, 768]
        assert args.no_photo_path is True
        assert args.max_images_per_file == 50

class TestPromptForDirectory:
    """Tests for interactive directory prompting."""

    @patch('builtins.input')
    @patch('images2kmz.cli.get_absolute_path')
    @patch('images2kmz.cli.Path.is_dir')
    def test_prompt_for_directory_valid(self, mock_isdir, mock_abspath, mock_input):
        """Test providing a valid existing directory."""
        mock_input.return_value = '/valid/path'
        mock_abspath.return_value = '/abs/valid/path'
        mock_isdir.return_value = True
        
        # Mock console to avoid output
        mock_console = Mock()
        
        result = prompt_for_directory(mock_console)
        
        assert result == '/abs/valid/path'
        mock_input.assert_called_once()

    @patch('builtins.input')
    @patch('images2kmz.cli.get_absolute_path')
    @patch('images2kmz.cli.Path.is_dir')
    @patch('images2kmz.cli.Path.mkdir')
    def test_prompt_for_directory_create(self, mock_mkdir, mock_isdir, mock_abspath, mock_input):
        """Test creating a non-existent directory."""
        # Sequence: path input -> confirmation 'y'
        mock_input.side_effect = ['/new/path', 'y']
        mock_abspath.return_value = '/abs/new/path'
        mock_isdir.return_value = False
        
        mock_console = Mock()
        
        result = prompt_for_directory(mock_console)
        
        assert result == '/abs/new/path'
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('builtins.input')
    @patch('images2kmz.cli.get_absolute_path')
    @patch('images2kmz.cli.Path.is_dir')
    @patch('images2kmz.cli.sys.exit')
    def test_prompt_for_directory_cancel(self, mock_exit, mock_isdir, mock_abspath, mock_input):
        """Test cancelling directory creation."""
        # Sequence: path input -> confirmation 'n'
        mock_input.side_effect = ['/new/path', 'n']
        mock_abspath.return_value = '/abs/new/path'
        mock_isdir.return_value = False
        
        mock_console = Mock()
        # Mock sys.exit to raise SystemExit so we break out of the loop
        mock_exit.side_effect = SystemExit(0)
        
        with pytest.raises(SystemExit):
            prompt_for_directory(mock_console)
        
        mock_exit.assert_called_once_with(0)

    @patch('builtins.input')
    @patch('images2kmz.cli.get_absolute_path')
    @patch('images2kmz.cli.Path.is_dir')
    def test_prompt_for_directory_empty_then_valid(self, mock_isdir, mock_abspath, mock_input):
        """Test handling empty input retry."""
        # Sequence: empty -> valid path
        mock_input.side_effect = ['', '/valid/path']
        mock_abspath.return_value = '/abs/valid/path'
        mock_isdir.return_value = True
        
        mock_console = Mock()
        
        result = prompt_for_directory(mock_console)
        
        assert result == '/abs/valid/path'
        assert mock_input.call_count == 2
        # Check that error message was printed
        assert any("Error: Path cannot be empty" in str(c) for c in mock_console.print.call_args_list)

class TestRunFunction:
    """Tests for the main run orchestration function."""

    def setup_method(self):
        """Setup common mocks."""
        self.mock_console_patch = patch('images2kmz.cli.Console')
        self.mock_console_cls = self.mock_console_patch.start()
        self.mock_console = Mock()
        self.mock_console.__enter__ = Mock(return_value=self.mock_console)
        self.mock_console.__exit__ = Mock(return_value=None)
        self.mock_console_cls.return_value = self.mock_console
        
        self.mock_pb_patch = patch('images2kmz.ui_handler.ProgressBar')
        self.mock_pb_cls = self.mock_pb_patch.start()
        self.mock_pb = Mock()
        self.mock_pb_cls.return_value = self.mock_pb
        
        self.mock_heic_patch = patch('images2kmz.cli.HEICHandler')
        self.mock_heic_cls = self.mock_heic_patch.start()
        self.mock_heic = Mock()
        self.mock_heic_cls.return_value = self.mock_heic
        # Default: found 0 HEIC files
        self.mock_heic.scan.return_value = 0
        
        self.mock_processor_patch = patch('images2kmz.cli.ImageProcessor')
        self.mock_processor_cls = self.mock_processor_patch.start()
        self.mock_processor = Mock()
        self.mock_processor_cls.return_value = self.mock_processor
        # Setup default returns for new methods
        self.mock_processor.get_no_gps.return_value = []
        self.mock_processor.get_no_direction.return_value = []
        
        self.mock_kmz_patch = patch('images2kmz.cli.KMZGenerator')
        self.mock_kmz_cls = self.mock_kmz_patch.start()
        self.mock_kmz = Mock()
        # Setup mock as context manager
        self.mock_kmz_cls.return_value = self.mock_kmz
        self.mock_kmz.__enter__ = Mock(return_value=self.mock_kmz)
        self.mock_kmz_cls.return_value.__exit__ = Mock(return_value=None)
        
        # Patch where it is defined, because it is imported locally in run()
        self.mock_get_files_patch = patch('images2kmz.image_processor.get_image_files')
        self.mock_get_files = self.mock_get_files_patch.start()
        
        self.mock_progress_patch = patch('images2kmz.cli.ProgressBar')
        self.mock_progress_cls = self.mock_progress_patch.start()
        self.mock_progress = Mock()
        self.mock_progress_cls.return_value = self.mock_progress

    def teardown_method(self):
        """Stop patches."""
        self.mock_console_patch.stop()
        self.mock_heic_patch.stop()
        self.mock_processor_patch.stop()
        self.mock_kmz_patch.stop()
        self.mock_get_files_patch.stop()
        self.mock_progress_patch.stop()

    @patch('images2kmz.cli.Path.is_dir')
    @patch('images2kmz.cli.get_absolute_path')
    def test_run_input_dir_not_found(self, mock_abspath, mock_isdir):
        """Test error when input directory doesn't exist."""
        mock_abspath.return_value = '/invalid/path'
        mock_isdir.return_value = False
        
        result = run(['/invalid/path'])
        
        assert result == 1
        # Check error message
        calls = [c for c in self.mock_console.print.call_args_list if "Error: Input directory does not exist" in str(c)]
        assert len(calls) > 0

    @patch('images2kmz.cli.Path.is_dir')
    @patch('images2kmz.cli.get_absolute_path')
    def test_run_success_no_images(self, mock_abspath, mock_isdir):
        """Test workflow when no images found."""
        mock_abspath.return_value = '/valid/path'
        mock_isdir.return_value = True
        self.mock_get_files.return_value = []
        
        # Setup processor mock stats
        self.mock_processor.get_stats.return_value = {
            'processed': 0, 'skipped_no_gps': 0, 'errors': 0
        }
        
        result = run(['/valid/path'])
        
        assert result == 0
        # Should not create KMZ generator
        self.mock_kmz_cls.assert_not_called()
        # Should print "No photos found"
        calls = [c for c in self.mock_console.print.call_args_list if "No photos with GPS data found" in str(c)]
        assert len(calls) > 0

    @patch('images2kmz.cli.Path.is_dir')
    @patch('images2kmz.cli.get_absolute_path')
    def test_run_success_with_images(self, mock_abspath, mock_isdir):
        """Test full successful workflow with images."""
        mock_abspath.return_value = '/valid/path'
        mock_isdir.return_value = True
        self.mock_get_files.return_value = ['img1.jpg', 'img2.jpg']
        
        # Mock processed data
        processed_data = [
            {
                'path': '/valid/path/img1.jpg',
                'gps': Mock(),
                'thumbnail': b'bytes',
                'filename': 'img1.jpg'
            },
            {
                'path': '/valid/path/img2.jpg',
                'gps': Mock(),
                'thumbnail': b'bytes',
                'filename': 'img2.jpg'
            }
        ]
        self.mock_processor.process_directory.return_value = processed_data
        
        # Mock stats
        self.mock_processor.get_stats.return_value = {
            'processed': 2, 'skipped_no_gps': 0, 'errors': 0
        }
        
        # Mock KMZ save
        self.mock_kmz.save.return_value = '/valid/path/photos.kmz'
        
        result = run(['/valid/path'])
        
        assert result == 0
        
        # Verify call chain
        self.mock_heic_cls.assert_called_once()
        self.mock_heic.scan.assert_called_once()
        
        self.mock_processor_cls.assert_called_once()
        self.mock_processor.process_directory.assert_called_once()
        
        # KMZ generation
        self.mock_kmz_cls.assert_called_once()
        assert self.mock_kmz.add_photo.call_count == 2
        self.mock_kmz.save.assert_called_once()

    @patch('images2kmz.cli.Path.is_dir')
    @patch('images2kmz.cli.get_absolute_path')
    @patch('images2kmz.cli.batch_convert_heic')
    def test_run_with_heic_conversion(self, mock_batch_convert, mock_abspath, mock_isdir):
        """Test HEIC auto-conversion workflow."""
        mock_abspath.return_value = '/valid/path'
        mock_isdir.return_value = True
        self.mock_get_files.return_value = []
        self.mock_processor.get_stats.return_value = {'processed': 0, 'skipped_no_gps': 0, 'errors': 0}
        
        # Mock HEIC files found
        self.mock_heic.scan.return_value = 5
        self.mock_heic.heic_files = ['file1.heic']
        
        result = run(['/valid/path'])
        
        assert result == 0
        mock_batch_convert.assert_called_once()

    @patch('images2kmz.cli.Path.is_dir')
    @patch('images2kmz.cli.get_absolute_path')
    def test_run_kmz_save_error(self, mock_abspath, mock_isdir):
        """Test handling of KMZ save errors."""
        mock_abspath.return_value = '/valid/path'
        mock_isdir.return_value = True
        self.mock_get_files.return_value = ['img1.jpg']
        
        # Mock successful processing
        self.mock_processor.process_directory.return_value = [
            {'path': 'p', 'gps': 'g', 'thumbnail': 't', 'filename': 'f'}
        ]
        self.mock_processor.get_stats.return_value = {'processed': 1, 'skipped_no_gps': 0, 'errors': 0}
        
        # Mock KMZ save failure
        self.mock_kmz.save.side_effect = Exception("Save failed")
        
        result = run(['/valid/path'])
        
        assert result == 1
        calls = [c for c in self.mock_console.print.call_args_list if "Error generating KMZ file" in str(c)]
        assert len(calls) > 0
        # Context manager handles cleanup automatically on exception
        # cleanup() is called in __exit__ which happens before the exception propagates

    @patch('images2kmz.cli.Path.is_dir')
    @patch('images2kmz.cli.get_absolute_path')
    def test_run_keyboard_interrupt(self, mock_abspath, mock_isdir):
        """Test graceful handling of KeyboardInterrupt."""
        mock_abspath.return_value = '/valid/path'
        mock_isdir.return_value = True
        self.mock_get_files.return_value = ['img1.jpg']
        
        # Mock ImageProcessor to raise KeyboardInterrupt during processing
        self.mock_processor.process_directory.side_effect = KeyboardInterrupt()
        
        result = run(['/valid/path'])
        
        assert result == 130
        # Check cancellation message
        calls = [c for c in self.mock_console.print.call_args_list if "Operation cancelled by user" in str(c)]
        assert len(calls) > 0
        
        # Verify KMZ cleanup was NOT called yet (because it wasn't created yet)
        self.mock_kmz_cls.assert_not_called()

    @patch('images2kmz.cli.Path.is_dir')
    @patch('images2kmz.cli.get_absolute_path')
    def test_run_keyboard_interrupt_during_kmz(self, mock_abspath, mock_isdir):
        """Test graceful handling of KeyboardInterrupt during KMZ generation."""
        mock_abspath.return_value = '/valid/path'
        mock_isdir.return_value = True
        self.mock_get_files.return_value = ['img1.jpg']
        
        # Mock successful processing
        self.mock_processor.process_directory.return_value = [
            {'path': 'p', 'gps': 'g', 'thumbnail': 't', 'filename': 'f'}
        ]
        self.mock_processor.get_stats.return_value = {'processed': 1, 'skipped_no_gps': 0, 'errors': 0}
        
        # Mock KMZ addition to raise KeyboardInterrupt
        self.mock_kmz.add_photo.side_effect = KeyboardInterrupt()
        
        result = run(['/valid/path'])
        
        assert result == 130
        # Context manager handles cleanup automatically via __exit__

    @patch('images2kmz.cli.prompt_for_directory')
    def test_run_interactive_mode(self, mock_prompt):
        """Test interactive mode (no args provided)."""
        mock_prompt.return_value = '/prompted/path'
        self.mock_get_files.return_value = []
        self.mock_processor.get_stats.return_value = {'processed': 0, 'skipped_no_gps': 0, 'errors': 0}
        
        # Call run() with empty list to simulate no CLI args
        run([])
        
        mock_prompt.assert_called_once()
        # Verify processing used the prompted path
        self.mock_heic_cls.assert_called_with('/prompted/path', False)


class TestMain:
    """Tests for entry point."""

    @patch('images2kmz.cli.run')
    @patch('sys.exit')
    def test_main(self, mock_exit, mock_run):
        """Verify main calls run and exits with its return code."""
        mock_run.return_value = 42
        main()
        mock_run.assert_called_once()
        mock_exit.assert_called_once_with(42)

class TestHelpers:
    """Tests for helper functions in CLI."""
    
    def test_print_header(self):
        """Verify header printing uses console."""
        mock_console = Mock()
        print_header(mock_console)
        assert mock_console.print.call_count >= 3
        
    def test_print_summary(self):
        """Verify summary printing."""
        mock_console = Mock()
        stats = {'processed': 5, 'skipped_no_gps': 2, 'errors': 1}
        mock_kmz = Mock()
        mock_kmz.get_formatted_file_size.return_value = "10 MB"
        
        print_summary(stats, mock_kmz, "/out.kmz", None, [], [], mock_console)
        
        # Verify key info printed
        calls = str(mock_console.print.call_args_list)
        assert "Processed: 5" in calls
        assert "Skipped: 2" in calls
        assert "Errors: 1" in calls
        assert "Output: out.kmz (10 MB)" in calls

def test_tui_argument_parsing():
    from images2kmz.cli import create_parser
    parser = create_parser()
    args = parser.parse_args(["--tui"])
    assert args.tui is True

    args2 = parser.parse_args([])
    assert args2.tui is False

