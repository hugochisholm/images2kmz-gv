from __future__ import annotations

import argparse
import os
import platform
import string
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Dict, List, Optional

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar as TextualProgressBar,
    RichLog,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from . import __version__
from .cli import execute_run
from .core import KMZGenerator
from .ui_handler import UIHandler
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)


class TextualUIHandler(UIHandler):
    def __init__(self, app: App):
        self.app = app

    def print_header(self) -> None:
        separator = "=" * 60
        self.app.call_from_thread(
            self.app.log_message, f"\n[bold magenta]{separator}[/bold magenta]"
        )
        self.app.call_from_thread(
            self.app.log_message,
            "[bold cyan]images2kmz - Geotagged Photo KMZ Generator[/bold cyan]",
        )
        self.app.call_from_thread(
            self.app.log_message, f"[bold magenta]{separator}[/bold magenta]\n"
        )

    def print_info(self, message: str) -> None:
        self.app.call_from_thread(self.app.log_message, message)

    def print_warning(self, message: str) -> None:
        self.app.call_from_thread(self.app.log_message, f"[yellow]{message}[/yellow]")

    def print_error(self, message: str) -> None:
        self.app.call_from_thread(
            self.app.log_message, f"[bold red]{message}[/bold red]"
        )

    def print_success(self, message: str) -> None:
        self.app.call_from_thread(self.app.log_message, f"[green]{message}[/green]")

    def start_progress(self, description: str, total: int) -> None:
        self.app.call_from_thread(self.app.start_progress, description, total)

    def update_progress(
        self, current: int, total: int, filename: str | None = None
    ) -> None:
        self.app.call_from_thread(self.app.update_progress, current, total, filename)

    def finish_progress(self) -> None:
        self.app.call_from_thread(self.app.finish_progress)

    def print_summary(
        self,
        processor_stats: Dict[str, Any],
        kmz_generator: Optional[KMZGenerator | List[KMZGenerator]],
        output_path: Optional[str | List[str]],
        csv_path: Optional[str] = None,
        no_gps: Optional[List[str]] = None,
        no_direction: Optional[List[str]] = None,
    ) -> None:
        separator = "=" * 60
        self.app.call_from_thread(
            self.app.log_message, f"\n[bold magenta]{separator}[/bold magenta]"
        )
        self.app.call_from_thread(
            self.app.log_message, "[bold magenta]Summary:[/bold magenta]"
        )
        self.app.call_from_thread(
            self.app.log_message, f"[bold magenta]{separator}[/bold magenta]"
        )

        # Processing stats
        processed = processor_stats["processed"]
        skipped = processor_stats["skipped_no_gps"]
        errors = processor_stats["errors"]

        if processed > 0:
            self.app.call_from_thread(
                self.app.log_message,
                f"[green]✓ Processed: {processed} photo{'s' if processed != 1 else ''} with GPS data[/green]",
            )

        if skipped > 0:
            self.app.call_from_thread(
                self.app.log_message,
                f"[yellow]⊗ Skipped: {skipped} photo{'s' if skipped != 1 else ''} (no GPS data)[/yellow]",
            )

        if errors > 0:
            self.app.call_from_thread(
                self.app.log_message,
                f"[red]✗ Errors: {errors} photo{'s' if errors != 1 else ''} (processing failed)[/red]",
            )

        # Output file info
        if processed > 0 and kmz_generator and output_path:
            kmz_gens = (
                kmz_generator if isinstance(kmz_generator, list) else [kmz_generator]
            )
            out_paths = output_path if isinstance(output_path, list) else [output_path]

            for gen, path in zip(kmz_gens, out_paths):
                file_size = gen.get_formatted_file_size()
                if file_size:
                    self.app.call_from_thread(
                        self.app.log_message,
                        f"[green]📦 Output: {Path(path).name} ({file_size})[/green]",
                    )
                else:
                    self.app.call_from_thread(
                        self.app.log_message,
                        f"[green]📦 Output: {Path(path).name}[/green]",
                    )
                self.app.call_from_thread(
                    self.app.log_message, f"   [dim]Path: {path}[/dim]"
                )

        # CSV output info
        if csv_path:
            self.app.call_from_thread(
                self.app.log_message, f"[green]📊 CSV: {Path(csv_path).name}[/green]"
            )
            self.app.call_from_thread(
                self.app.log_message, f"   [dim]Path: {csv_path}[/dim]"
            )

        # Files missing location and direction - side by side boxes
        def format_box_content(files: list[str] | None) -> str:
            if not files:
                return "[green]None![/green]"
            display_files = files[:50]
            content = "\n".join(f"  - {f}" for f in display_files)
            if len(files) > 50:
                content += f"\n  ... and {len(files) - 50} more"
            return content

        gps_content = format_box_content(no_gps)
        direction_content = format_box_content(no_direction)

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

        self.app.call_from_thread(
            self.app.log_message, "\n[bold]Files with missing data:[/bold]"
        )
        self.app.call_from_thread(
            self.app.log_message, Columns([gps_panel, direction_panel])
        )

        self.app.call_from_thread(
            self.app.log_message, f"[bold magenta]{separator}[/bold magenta]\n"
        )


class FilteredDirectoryTree(DirectoryTree):
    def __init__(self, path: str, **kwargs):
        super().__init__(path, **kwargs)

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if not path.name.startswith(".")]


class DirectoryPickerScreen(ModalScreen[str]):
    def __init__(self, start_path: str = ""):
        super().__init__()
        self.home_path = str(Path.home())

        initial_path = ""
        if start_path and os.path.exists(start_path):
            try:
                p = Path(start_path).expanduser().resolve()
                initial_path = str(p.parent if p.is_file() else p)
            except Exception:
                pass

        self.selected_path: str = initial_path or self.home_path

        if platform.system() == "Windows":
            drive = os.path.splitdrive(self.selected_path)[0] or "C:"
            self.tree_root = drive + "\\"
        else:
            self.tree_root = self.home_path

    def get_available_drives(self) -> list[str]:
        drives = []
        if platform.system() == "Windows":
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    drives.append(drive)
        return drives

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Select a Directory", classes="group-label")

            if platform.system() == "Windows":
                with Horizontal(id="drive-picker"):
                    for drive in self.get_available_drives():
                        # Using just the letter as ID to keep it simple
                        yield Button(drive, id=f"drive_{drive[0]}", classes="drive-btn")

            with Vertical(id="tree-container"):
                tree = FilteredDirectoryTree(self.tree_root, id="dir-tree")
                tree.guide_depth = 3
                yield tree
            yield Label(self.selected_path, id="current-path")
            with Horizontal(id="buttons"):
                yield Button("Cancel", variant="error", id="btn_cancel")
                yield Button("Select", variant="success", id="btn_select")

    async def update_tree_root(self, new_root: str) -> None:
        tree_container = self.query_one("#tree-container")
        await self.query_one("#dir-tree").remove()
        new_tree = FilteredDirectoryTree(new_root, id="dir-tree")
        new_tree.guide_depth = 3
        await tree_container.mount(new_tree)
        self.selected_path = new_root
        self.query_one("#current-path", Label).update(self.selected_path)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel":
            self.dismiss(None)
        elif event.button.id == "btn_select":
            self.dismiss(self.selected_path)
        elif event.button.id and event.button.id.startswith("drive_"):
            drive_letter = event.button.id.split("_")[1]
            new_root = f"{drive_letter}:\\"
            await self.update_tree_root(new_root)

    def on_tree_node_highlighted(self, event) -> None:
        if event.node.data:
            path = getattr(event.node.data, "path", None)
            if path:
                self.selected_path = str(path.parent if path.is_file() else path)
                self.query_one("#current-path", Label).update(self.selected_path)


class Images2KMZApp(App):
    TITLE = f"Images2KMZ (GeoVerra) {__version__} - TUI"

    CSS = """
    $gv-blue: #1E2D48;
    $gv-green: #A4CE3C;

    Screen {
        border: thick $gv-blue;
    }
    .form-container { padding: 1; height: 1fr; border-right: solid $gv-blue; }
    .log-container { height: 1fr; background: $surface; }
    #main-layout { layout: horizontal; }
    #left-pane { width: 40%; height: 1fr; }
    #right-pane { width: 60%; height: 1fr; }
    .pane-title {
        background: $gv-blue;
        color: $gv-green;
        text-align: center;
        text-style: bold;
        width: 100%;
        padding: 0 1;
        height: 1;
    }
    .group-container { 
        margin-bottom: 1; 
        padding: 1;
        height: auto;
    }
    .field-label {
        margin-top: 1;
        margin-bottom: 0;
        text-align: left;
        width: 100%;
        color: $gv-green;
        text-style: bold;
    }
    .input-row {
        height: auto;
        layout: horizontal;
    }
    .input-row Input {
        width: 1fr;
    }
    .input-row Button {
        width: 15;
        margin-left: 1;
    }
    Button {
        background: $gv-blue;
        color: $gv-green;
        border: none;
        height: 3;
        min-width: 8;
        padding: 0 1;
    }
    Button:hover {
        background: $gv-blue 80%;
    }
    #bottom-buttons {
        height: auto;
        layout: horizontal;
        margin-top: 1;
        padding: 1;
    }
    #bottom-buttons Button {
        width: 1fr;
        margin-right: 1;
    }
    TabbedContent {
        height: 1fr;
    }
    ProgressBar {
        width: 65;
        margin-bottom: 1;
        padding: 0;
        border: none;
    }
    ProgressBar Bar {
        width: 1fr;
    }
    ProgressBar Percentage {
        width: 5;
        text-align: right;
    }
    ProgressBar > .bar--bar {
        color: $gv-green;
    }
    ProgressBar > .bar--complete {
        color: $gv-green;
    }
    #progress_bar {
        display: none;
    }

    /* DirectoryPickerScreen styling */
    DirectoryPickerScreen {
        align: center middle;
        background: $background 80%;
    }
    #dialog {
        width: 80%;
        height: 80%;
        border: thick $gv-blue;
        background: $surface;
        padding: 1;
    }
    #tree-container {
        height: 1fr;
        border: solid $gv-blue;
        margin-bottom: 1;
    }
    #drive-picker {
        height: auto;
        margin-bottom: 1;
        background: $surface;
        padding: 0 1;
        layout: horizontal;
    }
    .drive-btn {
        min-width: 4;
        height: 1;
        margin: 0 1;
        padding: 0 1;
        background: $gv-blue;
        color: $gv-green;
        text-style: none;
        border: none;
    }
    #current-path {
        width: 100%;
        text-align: center;
        margin-bottom: 1;
        color: $text-muted;
    }
    #buttons {
        height: auto;
        align: center middle;
        layout: horizontal;
    }
    #buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, parser: argparse.ArgumentParser):
        super().__init__()
        self.parser = parser
        self.inputs = {}
        self._active_inline_pb: TextualProgressBar | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-layout"):
            with Vertical(id="left-pane"):
                yield Label("Options", classes="pane-title")
                with VerticalScroll(classes="form-container", id="form-container"):
                    # Path fields always visible
                    yield Label("Input Directory", classes="field-label")
                    with Horizontal(classes="input-row"):
                        yield self.create_widget_by_dest("input_dir")
                        yield Button(
                            "Browse",
                            id="browse_input_dir",
                            variant="primary",
                        )

                    yield Label("Output Directory", classes="field-label")
                    with Horizontal(classes="input-row"):
                        yield self.create_widget_by_dest("output")
                        yield Button("Browse", id="browse_output", variant="primary")

                    with TabbedContent():
                        with TabPane("Processing"):
                            yield Label("Thumbnail Size", classes="field-label")
                            yield self.create_widget_by_dest("thumbnail_size")
                            yield Label("Maximum Images per KMZ", classes="field-label")
                            yield self.create_widget_by_dest("max_images")
                            yield Label("Export CSV", classes="field-label")
                            yield self.create_widget_by_dest("csv")
                            yield Label("Include Subdirectories", classes="field-label")
                            yield self.create_widget_by_dest("recursive")

                        with TabPane("Placemarks"):
                            yield Label("Preset", classes="field-label")
                            yield self.create_widget_by_dest("preset")
                            yield Label("Hide Photo Path", classes="field-label")
                            yield self.create_widget_by_dest("no_photo_path")

                        with TabPane("Advanced"):
                            yield Label("Coordinate System", classes="field-label")
                            yield self.create_widget_by_dest("coordinate_system")
                            yield Label("Enable Log File", classes="field-label")
                            yield self.create_widget_by_dest("log_file")
                            yield Label("Verbose Output", classes="field-label")
                            yield self.create_widget_by_dest("verbose")

                with Horizontal(id="bottom-buttons"):
                    yield Button("Run", id="btn_run", variant="success")
                    yield Button("Exit", id="btn_exit", variant="error")

            with Vertical(id="right-pane", classes="log-container"):
                yield Label("Progress Log", classes="pane-title")
                yield VerticalScroll(id="log_view")

        yield Footer()

    def create_widget_by_dest(self, dest: str):
        actions_by_dest = {action.dest: action for action in self.parser._actions}
        action = actions_by_dest.get(dest)
        if not action:
            return Static(f"Unknown: {dest}")

        if isinstance(action, argparse._StoreTrueAction):
            value = action.default
            if dest == "csv":
                value = True
            cb = Checkbox("", id=f"input_{action.dest}", value=value)
            self.inputs[action.dest] = cb
            return cb
        elif action.choices:
            options = [(str(c), str(c)) for c in action.choices]

            default_val = action.default
            if dest == "preset" and default_val is None:
                default_val = "full"

            # Use value in constructor to ensure it is selected on startup
            # and set allow_blank=False for these required choices
            initial_value = (
                str(default_val) if default_val is not None else Select.BLANK
            )
            sel = Select(
                options,
                prompt="",
                id=f"input_{action.dest}",
                value=initial_value,
                allow_blank=False if default_val is not None else True,
            )

            self.inputs[action.dest] = sel
            return sel
        else:
            default_val = str(action.default) if action.default is not None else ""
            placeholder = ""
            if action.dest == "output":
                default_val = ""
                placeholder = (
                    "Leave this field blank to place the output in the same directory"
                )
            elif isinstance(action.default, list):
                default_val = ",".join(map(str, action.default))

            inp = Input(
                value=default_val, placeholder=placeholder, id=f"input_{action.dest}"
            )
            self.inputs[action.dest] = inp
            return inp

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_run":
            # Construct namespace
            args_dict = {}
            actions_by_dest = {action.dest: action for action in self.parser._actions}

            for dest, widget in self.inputs.items():
                if isinstance(widget, Checkbox):
                    args_dict[dest] = widget.value
                elif isinstance(widget, Select):
                    # Handle empty select correctly. All valid options are strings.
                    # Textual uses Select.BLANK (which is a NoSelection sentinel) for empty selection.
                    val = widget.value
                    if isinstance(val, str):
                        args_dict[dest] = val
                    else:
                        # Fallback to argparse default if empty
                        action = actions_by_dest.get(dest)
                        args_dict[dest] = action.default if action else None
                elif isinstance(widget, Input):
                    val = widget.value
                    if dest == "max_images":
                        try:
                            args_dict[dest] = int(val)
                        except ValueError:
                            args_dict[dest] = 100
                    else:
                        if not val:
                            # Fallback to argparse default if empty
                            action = actions_by_dest.get(dest)
                            args_dict[dest] = action.default if action else None
                        else:
                            args_dict[dest] = val

            if not args_dict.get("input_dir"):
                self.log_message(
                    "[bold red]Error: Input Directory is required.[/bold red]"
                )
                return

            self.query_one("#form-container").disabled = True

            namespace = argparse.Namespace(**args_dict)
            self.run_processing(namespace)

        elif event.button.id == "btn_exit":
            self.exit()

        elif event.button.id in ("browse_input_dir", "browse_output"):
            dest = event.button.id.replace("browse_", "")
            input_widget = self.inputs.get(dest)
            start_path = (
                input_widget.value if input_widget and input_widget.value else ""
            )

            def set_path(path: str | None) -> None:
                if path is not None and input_widget:
                    input_widget.value = path

            self.push_screen(DirectoryPickerScreen(start_path=start_path), set_path)

    @work(thread=True)
    def run_processing(self, parsed_args: argparse.Namespace) -> None:
        ui = TextualUIHandler(self)
        try:
            execute_run(parsed_args, ui)
        except Exception as e:
            self.call_from_thread(self.log_message, f"[red]Critical Error: {e}[/red]")
        finally:
            self.call_from_thread(self.enable_form)

    def log_message(self, message: Any) -> None:
        log_view = self.query_one("#log_view", VerticalScroll)
        if isinstance(message, str):
            log_view.mount(Static(message, markup=True))
        else:
            log_view.mount(Static(message))
        log_view.scroll_end(animate=False)

    def start_progress(self, description: str, total: int) -> None:
        log_view = self.query_one("#log_view", VerticalScroll)
        log_view.mount(Label(f"\n[cyan]{description}...[/cyan]"))

        # Create inline progress bar
        self._active_inline_pb = TextualProgressBar(
            total=total, show_eta=False, show_percentage=True
        )
        log_view.mount(self._active_inline_pb)
        log_view.scroll_end(animate=False)

    def update_progress(
        self, current: int, total: int | None = None, filename: str | None = None
    ) -> None:
        if self._active_inline_pb:
            self._active_inline_pb.progress = current
            if total is not None:
                self._active_inline_pb.total = total

    def finish_progress(self) -> None:
        if self._active_inline_pb:
            if self._active_inline_pb.total is not None:
                self._active_inline_pb.progress = self._active_inline_pb.total
            self._active_inline_pb = None

        log_view = self.query_one("#log_view", VerticalScroll)
        log_view.scroll_end(animate=False)

    def enable_form(self) -> None:
        self.query_one("#form-container").disabled = False


def run_tui(parser: argparse.ArgumentParser) -> int:
    app = Images2KMZApp(parser)
    app.run()
    return 0
