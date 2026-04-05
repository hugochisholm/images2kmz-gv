from typing import Protocol, Any, Dict, Optional, List
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns

from .core import KMZGenerator
from .progress import ProgressBar

class UIHandler(Protocol):
    def print_header(self) -> None: ...
    def print_info(self, message: str) -> None: ...
    def print_warning(self, message: str) -> None: ...
    def print_error(self, message: str) -> None: ...
    def print_success(self, message: str) -> None: ...
    def start_progress(self, description: str, total: int) -> None: ...
    def update_progress(self, current: int, total: int, filename: str | None = None) -> None: ...
    def finish_progress(self) -> None: ...
    def print_summary(
        self,
        processor_stats: Dict[str, Any],
        kmz_generator: Optional[KMZGenerator],
        output_path: Optional[str],
        csv_path: Optional[str] = None,
        no_gps: Optional[List[str]] = None,
        no_direction: Optional[List[str]] = None,
    ) -> None: ...

class RichUIHandler:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.progress_bar: Optional[ProgressBar] = None

    def print_header(self) -> None:
        separator = "=" * 60
        self.console.print(f"\n[bold magenta]{separator}[/bold magenta]")
        self.console.print("[bold cyan]images2kmz - Geotagged Photo KMZ Generator[/bold cyan]")
        self.console.print(f"[bold magenta]{separator}[/bold magenta]\n")

    def print_info(self, message: str) -> None:
        self.console.print(message)

    def print_warning(self, message: str) -> None:
        self.console.print(f"[yellow]{message}[/yellow]")

    def print_error(self, message: str) -> None:
        self.console.print(f"[bold red]{message}[/bold red]")

    def print_success(self, message: str) -> None:
        self.console.print(f"[green]{message}[/green]")

    def start_progress(self, description: str, total: int) -> None:
        self.progress_bar = ProgressBar(description, console=self.console)
        self.progress_bar.start(total)

    def update_progress(self, current: int, total: int, filename: str | None = None) -> None:
        if self.progress_bar:
            self.progress_bar.update(current, total, filename)

    def finish_progress(self) -> None:
        if self.progress_bar:
            self.progress_bar.finish()
            self.progress_bar = None

    def print_summary(
        self,
        processor_stats: Dict[str, Any],
        kmz_generator: Optional[KMZGenerator],
        output_path: Optional[str],
        csv_path: Optional[str] = None,
        no_gps: Optional[List[str]] = None,
        no_direction: Optional[List[str]] = None,
    ) -> None:
        # We need to format the summary carefully to match the existing print_summary
        separator = "=" * 60
        self.console.print(f"\n[bold magenta]{separator}[/bold magenta]")
        self.console.print("[bold magenta]Summary:[/bold magenta]")
        self.console.print(f"[bold magenta]{separator}[/bold magenta]")
        
        # Processing stats
        processed = processor_stats['processed']
        skipped = processor_stats['skipped_no_gps']
        errors = processor_stats['errors']
        
        if processed > 0:
            self.console.print(f"[green]✓ Processed: {processed} photo{'s' if processed != 1 else ''} with GPS data[/green]")
        
        if skipped > 0:
            self.console.print(f"[yellow]⊗ Skipped: {skipped} photo{'s' if skipped != 1 else ''} (no GPS data)[/yellow]")
        
        if errors > 0:
            self.console.print(f"[red]✗ Errors: {errors} photo{'s' if errors != 1 else ''} (processing failed)[/red]")
        
        # Output file info
        if processed > 0 and kmz_generator and output_path:
            file_size = kmz_generator.get_formatted_file_size()
            if file_size:
                self.console.print(f"[green]📦 Output: {Path(output_path).name} ({file_size})[/green]")
            else:
                self.console.print(f"[green]📦 Output: {Path(output_path).name}[/green]")
            self.console.print(f"   [dim]Path: {output_path}[/dim]")
        else:
            self.console.print("\n[bold yellow]⚠ No photos with GPS data found. KMZ file not created.[/bold yellow]")
        
        # CSV output info
        if csv_path:
            self.console.print(f"[green]📊 CSV: {Path(csv_path).name}[/green]")
            self.console.print(f"   [dim]Path: {csv_path}[/dim]")
        
        # Files missing location and direction - side by side boxes
        if no_gps is None:
            no_gps = []
        if no_direction is None:
            no_direction = []
        
        def format_box_content(files: list[str], box_title: str) -> str:
            if not files:
                return "[green]None![/green]"
            display_files = files[:50]
            content = "\\n".join(f"  - {f}" for f in display_files)
            if len(files) > 50:
                content += f"\\n  ... and {len(files) - 50} more"
            return content
        
        gps_content = format_box_content(no_gps, "Files missing location")
        direction_content = format_box_content(no_direction, "Files missing direction")
        
        gps_panel = Panel(
            gps_content,
            title="[bold]Files missing location[/bold]",
            border_style="yellow",
            padding=(0, 1),
            width=40,
        )
        direction_panel = Panel(
            direction_content,
            title="[bold]Files missing direction[/bold]",
            border_style="cyan",
            padding=(0, 1),
            width=40,
        )
        
        self.console.print("\n[bold]Files with missing data:[/bold]")
        self.console.print(Columns([gps_panel, direction_panel]))
        self.console.print(f"[bold magenta]{separator}[/bold magenta]\n")
