from __future__ import annotations

import argparse
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

from .cli import execute_run
from .core import KMZGenerator
from .ui_handler import UIHandler

class TextualUIHandler(UIHandler):
    def __init__(self, app: App):
        self.app = app

    def print_header(self) -> None:
        self.app.call_from_thread(self.app.log_message, "=== images2kmz ===")

    def print_info(self, message: str) -> None:
        self.app.call_from_thread(self.app.log_message, message)

    def print_warning(self, message: str) -> None:
        self.app.call_from_thread(self.app.log_message, f"[yellow]{message}[/yellow]")

    def print_error(self, message: str) -> None:
        self.app.call_from_thread(self.app.log_message, f"[red]{message}[/red]")

    def print_success(self, message: str) -> None:
        self.app.call_from_thread(self.app.log_message, f"[green]{message}[/green]")

    def start_progress(self, description: str, total: int) -> None:
        self.app.call_from_thread(self.app.start_progress, description, total)

    def update_progress(self, current: int, total: int, filename: str | None = None) -> None:
        self.app.call_from_thread(self.app.update_progress, current)

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
        self.app.call_from_thread(self.app.log_message, f"\nSummary: Processed {processor_stats['processed']} files.")
        if processor_stats['skipped_no_gps'] > 0:
            self.app.call_from_thread(self.app.log_message, f"[yellow]Skipped {processor_stats['skipped_no_gps']} files (no GPS data)[/yellow]")
        if output_path:
            out_paths = output_path if isinstance(output_path, list) else [output_path]
            for path in out_paths:
                self.app.call_from_thread(self.app.log_message, f"[green]KMZ saved to: {path}[/green]")
        if csv_path:
            self.app.call_from_thread(self.app.log_message, f"[green]CSV saved to: {csv_path}[/green]")


class FilteredDirectoryTree(DirectoryTree):
    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if not path.name.startswith(".")]

class DirectoryPickerScreen(ModalScreen[str]):
    CSS = """
    DirectoryPickerScreen {
        align: center middle;
        background: $background 80%;
    }
    #dialog {
        width: 80%;
        height: 80%;
        border: thick $background;
        background: $surface;
        padding: 1;
    }
    #tree-container {
        height: 1fr;
        border: solid $primary;
        margin-bottom: 1;
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
    }
    #buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, start_path: str = ""):
        super().__init__()
        if start_path and start_path != ".":
            try:
                self.start_path = str(Path(start_path).expanduser().resolve())
            except Exception:
                self.start_path = str(Path.home())
        else:
            self.start_path = str(Path.home())
        self.selected_path: str = self.start_path

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Select a Directory", classes="group-label")
            with Vertical(id="tree-container"):
                tree = FilteredDirectoryTree(self.start_path, id="dir-tree")
                tree.guide_depth = 3
                yield tree
            yield Label(self.start_path, id="current-path")
            with Horizontal(id="buttons"):
                yield Button("Cancel", variant="error", id="btn_cancel")
                yield Button("Select", variant="success", id="btn_select")

    def on_tree_node_highlighted(self, event) -> None:
        if event.node.data:
            path = getattr(event.node.data, "path", None)
            if path:
                self.selected_path = str(path.parent if path.is_file() else path)
                self.query_one("#current-path", Label).update(self.selected_path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel":
            self.dismiss(None)
        elif event.button.id == "btn_select":
            self.dismiss(self.selected_path)


class Images2KMZApp(App):
    TITLE = "Images2KMZ - TUI"
    
    CSS = """
    .form-container { padding: 1; height: 1fr; border-right: solid $accent; }
    .log-container { height: 1fr; background: $surface; }
    #main-layout { layout: horizontal; }
    #left-pane { width: 40%; height: 1fr; }
    #right-pane { width: 60%; height: 1fr; }
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
        color: $accent;
        font-style: bold;
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
    """

    def __init__(self, parser: argparse.ArgumentParser):
        super().__init__()
        self.parser = parser
        self.inputs = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-layout"):
            with Vertical(id="left-pane"):
                with VerticalScroll(classes="form-container", id="form-container"):
                    # Path fields always visible
                    yield Label("Input Directory", classes="field-label")
                    with Horizontal(classes="input-row"):
                        yield self.create_widget_by_dest("input_dir")
                        yield Button("Browse", id="browse_input_dir", variant="primary")
                    
                    yield Label("Output Directory", classes="field-label")
                    with Horizontal(classes="input-row"):
                        yield self.create_widget_by_dest("output")
                        yield Button("Browse", id="browse_output", variant="primary")

                    with TabbedContent():
                        with TabPane("Processing"):
                            yield Label("Thumbnail Size", classes="field-label")
                            yield self.create_widget_by_dest("thumbnail_size")
                            yield Label("Max Images", classes="field-label")
                            yield self.create_widget_by_dest("max_images")
                            yield self.create_widget_by_dest("recursive")
                        
                        with TabPane("Placemarks"):
                            yield Label("Preset", classes="field-label")
                            yield self.create_widget_by_dest("preset")
                            yield Label("Placemark Fields", classes="field-label")
                            yield self.create_widget_by_dest("placemark_fields")
                            yield self.create_widget_by_dest("no_photo_path")
                        
                        with TabPane("Advanced"):
                            yield self.create_widget_by_dest("csv")
                            yield Label("Coordinate System", classes="field-label")
                            yield self.create_widget_by_dest("coordinate_system")
                            yield self.create_widget_by_dest("log_file")
                            yield self.create_widget_by_dest("verbose")
                
                with Horizontal(id="bottom-buttons"):
                    yield Button("Run", id="btn_run", variant="success")
                    yield Button("Exit", id="btn_exit", variant="error")
            
            with Vertical(id="right-pane", classes="log-container"):
                yield TextualProgressBar(id="progress_bar", show_eta=False)
                yield RichLog(id="log_view", markup=True)
        
        yield Footer()

    def create_widget_by_dest(self, dest: str):
        actions_by_dest = {action.dest: action for action in self.parser._actions}
        action = actions_by_dest.get(dest)
        if not action: return Static(f"Unknown: {dest}")

        friendly_labels = {
            "input_dir": "Input Directory",
            "output": "Output Directory",
            "recursive": "Include Subdirectories",
            "thumbnail_size": "Thumbnail Size Preset",
            "preset": "Placemark Preset",
            "placemark_fields": "Placemark Fields",
            "no_photo_path": "Hide Photo Path",
            "csv": "Export CSV",
            "coordinate_system": "Coordinate System",
            "log_file": "Enable Log File",
            "max_images": "Max Images Per File",
            "verbose": "Verbose Output",
        }
        label = friendly_labels.get(action.dest, action.dest)
        
        if isinstance(action, argparse._StoreTrueAction):
            cb = Checkbox(label, id=f"input_{action.dest}", value=action.default)
            self.inputs[action.dest] = cb
            return cb
        elif action.choices:
            options = [(str(c), str(c)) for c in action.choices]
            sel = Select(options, prompt="Select...", id=f"input_{action.dest}")
            if action.default:
                sel.value = str(action.default)
            self.inputs[action.dest] = sel
            return sel
        else:
            default_val = str(action.default) if action.default is not None else ""
            if action.dest == "output":
                default_val = ""
            elif isinstance(action.default, list):
                default_val = ",".join(map(str, action.default))
            inp = Input(value=default_val, id=f"input_{action.dest}")
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
                    if dest == 'max_images':
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

            if not args_dict.get('input_dir'):
                self.log_message("[bold red]Error: Input Directory is required.[/bold red]")
                return

            self.query_one("#form-container").disabled = True
            
            namespace = argparse.Namespace(**args_dict)
            self.run_processing(namespace)

        elif event.button.id == "btn_exit":
            self.exit()

        elif event.button.id in ("browse_input_dir", "browse_output"):
            dest = event.button.id.replace("browse_", "")
            input_widget = self.inputs.get(dest)
            start_path = input_widget.value if input_widget and input_widget.value else ""
            
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

    def log_message(self, message: str) -> None:
        self.query_one(RichLog).write(message)
        
    def start_progress(self, description: str, total: int) -> None:
        pb = self.query_one(TextualProgressBar)
        pb.total = total
        pb.progress = 0
        self.log_message(f"[cyan]{description}...[/cyan]")
        
    def update_progress(self, current: int) -> None:
        self.query_one(TextualProgressBar).progress = current
        
    def finish_progress(self) -> None:
        pb = self.query_one(TextualProgressBar)
        if pb.total is not None:
            pb.progress = pb.total
        
    def enable_form(self) -> None:
        self.query_one("#form-container").disabled = False

def run_tui(parser: argparse.ArgumentParser) -> int:
    app = Images2KMZApp(parser)
    app.run()
    return 0
