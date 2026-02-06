"""Progress bar utilities using rich library."""

from typing import Optional, Callable
from rich.progress import (
    Progress as RichProgress,
    BarColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.console import Console


class ProgressBar:
    """
    Wrapper around rich Progress for displaying file processing
    progress with percentage and filename display.
    """

    def __init__(self, description: str):
        """
        Initialize progress bar.

        Args:
            description: Description text to display (e.g., "Processing")
        """
        self.console = Console()
        self.progress = RichProgress(
            TextColumn("[cyan]{task.description}[/cyan]"),
            BarColumn(complete_style="green", finished_style="green"),
            TaskProgressColumn(),
            TextColumn(""),  # For filename
            console=self.console,
            transient=False,  # Keep progress bar visible after complete
        )
        self.description = description
        self.task_id = None
        self.started = False

    def start(self, total: int) -> None:
        """
        Start progress tracking with total count.

        Args:
            total: Total number of items to process
        """
        if not self.started:
            self.progress.start()
            self.task_id = self.progress.add_task(self.description, total=total)
            self.started = True

    def update(
        self, current: int, total: int, filename: Optional[str] = None
    ) -> None:
        """
        Update progress with current count and optional filename.

        Args:
            current: Current item number
            total: Total number of items
            filename: Optional filename being processed
        """
        if filename:
            desc = f"{self.description} [{filename}]"
        else:
            desc = self.description

        self.progress.update(self.task_id, completed=current, total=total, description=desc)

    def finish(self) -> None:
        """Mark progress as complete and close the progress display."""
        self.progress.stop()


def create_progress_callback(progress_bar: ProgressBar) -> Callable:
    """
    Create a callback function for progress tracking.

    Args:
        progress_bar: ProgressBar instance to update

    Returns:
        Callback function with signature: callback(current, total, filename)
    """

    def callback(current: int, total: int, filename: Optional[str] = None) -> None:
        progress_bar.update(current, total, filename)

    return callback
