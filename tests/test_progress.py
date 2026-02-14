"""Unit tests for images2kmz.progress module."""

import sys
from unittest.mock import Mock, patch, MagicMock
import pytest

from rich.console import Console
from rich.progress import (
    Progress as RichProgress,
    BarColumn,
    TaskProgressColumn,
    TextColumn,
)

from images2kmz.progress import ProgressBar, create_progress_callback


class TestProgressBar:
    """Tests for ProgressBar class."""

    def test_init_with_console(self):
        """
        Test initialization with provided console.

        Should use the provided console and create RichProgress with correct configuration.
        """
        mock_console = Mock(spec=Console)

        with patch('images2kmz.progress.RichProgress') as mock_rich_progress:
            mock_progress_instance = Mock()
            mock_rich_progress.return_value = mock_progress_instance

            pb = ProgressBar("Processing", console=mock_console)

            # Verify state
            assert pb.console is mock_console
            assert pb.task_id is None
            assert pb.started is False
            assert pb.description == "Processing"

            # Verify RichProgress created with correct parameters
            mock_rich_progress.assert_called_once()
            call_kwargs = mock_rich_progress.call_args

            # Check columns are correct types
            columns = call_kwargs[0]
            assert isinstance(columns[0], TextColumn)
            assert isinstance(columns[1], BarColumn)
            assert isinstance(columns[2], TaskProgressColumn)
            assert isinstance(columns[3], TextColumn)

            # Check keyword arguments
            assert call_kwargs[1]['console'] is mock_console
            assert call_kwargs[1]['transient'] is False

    def test_init_without_console(self):
        """
        Test initialization without console parameter.

        Should create a new Console instance automatically.
        """
        with patch('images2kmz.progress.RichProgress') as mock_rich_progress, \
             patch('images2kmz.progress.Console') as mock_console_class:
            mock_progress_instance = Mock()
            mock_rich_progress.return_value = mock_progress_instance
            mock_console_instance = Mock(spec=Console)
            mock_console_class.return_value = mock_console_instance

            pb = ProgressBar("Test")

            # Verify new Console was created
            mock_console_class.assert_called_once()
            assert pb.console is mock_console_instance

    def test_start_initializes_progress(self):
        """
        Test that start() initializes progress tracking.

        Should call progress.start() and add_task() with correct parameters.
        """
        mock_console = Mock(spec=Console)
        mock_progress_instance = Mock()
        mock_progress_instance.add_task.return_value = 42  # task_id

        with patch('images2kmz.progress.RichProgress', return_value=mock_progress_instance):
            pb = ProgressBar("Processing", console=mock_console)
            pb.start(total=10)

            # Verify progress methods called
            mock_progress_instance.start.assert_called_once()
            mock_progress_instance.add_task.assert_called_once_with(
                "Processing", total=10
            )

            # Verify state updated
            assert pb.started is True
            assert pb.task_id == 42

    def test_start_already_started_does_not_reinitialize(self):
        """
        Test that calling start() twice doesn't reinitialize.

        Second call should be ignored since already started.
        """
        mock_console = Mock(spec=Console)
        mock_progress_instance = Mock()
        mock_progress_instance.add_task.return_value = 1

        with patch('images2kmz.progress.RichProgress', return_value=mock_progress_instance):
            pb = ProgressBar("Processing", console=mock_console)

            # First start
            pb.start(10)
            assert mock_progress_instance.start.call_count == 1
            assert mock_progress_instance.add_task.call_count == 1

            # Second start should not call methods again
            pb.start(20)
            assert mock_progress_instance.start.call_count == 1
            assert mock_progress_instance.add_task.call_count == 1

    def test_update_with_filename_updates_description(self):
        """
        Test update() with filename includes it in description.

        Description should be "Description [filename]".
        """
        mock_console = Mock(spec=Console)
        mock_progress_instance = Mock()
        mock_progress_instance.add_task.return_value = 1

        with patch('images2kmz.progress.RichProgress', return_value=mock_progress_instance):
            pb = ProgressBar("Processing", console=mock_console)
            pb.start(10)
            pb.update(current=5, total=10, filename="photo.jpg")

            mock_progress_instance.update.assert_called_once_with(
                1, completed=5, total=10, description="Processing [photo.jpg]"
            )

    def test_update_without_filename_uses_base_description(self):
        """
        Test update() without filename uses base description.

        Description should be just "Description" without brackets.
        """
        mock_console = Mock(spec=Console)
        mock_progress_instance = Mock()
        mock_progress_instance.add_task.return_value = 1

        with patch('images2kmz.progress.RichProgress', return_value=mock_progress_instance):
            pb = ProgressBar("Processing", console=mock_console)
            pb.start(10)
            pb.update(current=5, total=10)

            mock_progress_instance.update.assert_called_once_with(
                1, completed=5, total=10, description="Processing"
            )

    def test_update_before_start_returns_early(self):
        """
        Test update() before start() returns early without error.

        Since task_id is None, should not call progress.update().
        """
        mock_console = Mock(spec=Console)
        mock_progress_instance = Mock()

        with patch('images2kmz.progress.RichProgress', return_value=mock_progress_instance):
            pb = ProgressBar("Processing", console=mock_console)
            # Don't call start()

            # Should not raise error
            pb.update(1, 10, "file.jpg")

            # progress.update should not be called
            mock_progress_instance.update.assert_not_called()

    def test_finish_stops_progress(self):
        """
        Test finish() stops the progress display.

        Should call progress.stop() once.
        """
        mock_console = Mock(spec=Console)
        mock_progress_instance = Mock()

        with patch('images2kmz.progress.RichProgress', return_value=mock_progress_instance):
            pb = ProgressBar("Processing", console=mock_console)
            pb.start(10)
            pb.finish()

            mock_progress_instance.stop.assert_called_once()

    def test_multiple_updates_progress(self):
        """
        Test multiple sequential updates.

        Each update should call progress.update() with correct parameters.
        """
        mock_console = Mock(spec=Console)
        mock_progress_instance = Mock()
        mock_progress_instance.add_task.return_value = 1

        with patch('images2kmz.progress.RichProgress', return_value=mock_progress_instance):
            pb = ProgressBar("Processing", console=mock_console)
            pb.start(10)

            pb.update(1, 10, "file1.jpg")
            pb.update(2, 10, "file2.jpg")
            pb.update(3, 10)

            assert mock_progress_instance.update.call_count == 3

            # Verify each call
            calls = mock_progress_instance.update.call_args_list
            assert calls[0] == ((1,), {'completed': 1, 'total': 10, 'description': 'Processing [file1.jpg]'})
            assert calls[1] == ((1,), {'completed': 2, 'total': 10, 'description': 'Processing [file2.jpg]'})
            assert calls[2] == ((1,), {'completed': 3, 'total': 10, 'description': 'Processing'})

    def test_finish_before_start(self):
        """
        Test finish() before start() handles gracefully.

        Should not crash even if progress was never started.
        """
        mock_console = Mock(spec=Console)
        mock_progress_instance = Mock()

        with patch('images2kmz.progress.RichProgress', return_value=mock_progress_instance):
            pb = ProgressBar("Processing", console=mock_console)
            # Don't call start()

            # Should not raise error
            pb.finish()

            # progress.stop should still be called (on the instance)
            mock_progress_instance.stop.assert_called_once()


class TestCreateProgressCallback:
    """Tests for create_progress_callback function."""

    def test_callback_creation_and_invocation(self):
        """
        Test callback creation and proper invocation.

        Callback should call progress_bar.update() with correct arguments.
        """
        mock_progress_bar = Mock(spec=ProgressBar)

        callback = create_progress_callback(mock_progress_bar)

        # Verify callback is callable
        assert callable(callback)

        # Invoke callback
        callback(5, 10, "test.jpg")

        # Verify update called correctly
        mock_progress_bar.update.assert_called_once_with(5, 10, "test.jpg")

    def test_callback_without_filename(self):
        """
        Test callback invocation without filename parameter.

        Should pass None for filename.
        """
        mock_progress_bar = Mock(spec=ProgressBar)

        callback = create_progress_callback(mock_progress_bar)
        callback(3, 5)

        mock_progress_bar.update.assert_called_once_with(3, 5, None)


class TestProgressBarIntegration:
    """Integration tests for ProgressBar with actual Rich library."""

    def test_integration_in_non_tty_environment(self):
        """
        Integration test that works in non-TTY environments.

        Rich automatically detects non-TTY and handles gracefully.
        Should complete without errors.
        """
        # This test runs with actual Rich library (not mocked)
        # In non-TTY environments, Rich falls back to simple output

        pb = ProgressBar("Test Processing")

        try:
            pb.start(3)
            pb.update(1, 3, "file1.jpg")
            pb.update(2, 3, "file2.jpg")
            pb.update(3, 3)
            pb.finish()
            # If we get here without exception, test passes
            assert True
        except Exception as e:
            pytest.fail(f"Integration test failed with exception: {e}")

        # Verify state is correct after operations
        assert pb.started is True
        assert pb.task_id is not None
