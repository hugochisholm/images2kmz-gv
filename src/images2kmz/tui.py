import argparse
from typing import Dict, Any, Optional, List
from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Checkbox, Select, Button, RichLog, ProgressBar as TextualProgressBar
from textual.containers import VerticalScroll, Vertical
from textual import work

from .ui_handler import UIHandler
from .core import KMZGenerator
from .cli import execute_run


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
        kmz_generator: Optional[KMZGenerator],
        output_path: Optional[str],
        csv_path: Optional[str] = None,
        no_gps: Optional[List[str]] = None,
        no_direction: Optional[List[str]] = None,
    ) -> None:
        self.app.call_from_thread(self.app.log_message, f"\\nSummary: Processed {processor_stats['processed']} files.")
        if processor_stats['skipped_no_gps'] > 0:
            self.app.call_from_thread(self.app.log_message, f"[yellow]Skipped {processor_stats['skipped_no_gps']} files (no GPS data)[/yellow]")
        if output_path:
            self.app.call_from_thread(self.app.log_message, f"[green]KMZ saved to: {output_path}[/green]")
        if csv_path:
            self.app.call_from_thread(self.app.log_message, f"[green]CSV saved to: {csv_path}[/green]")


class Images2KMZApp(App):
    CSS = """
    .form-container { padding: 1; height: auto; }
    .log-container { height: 1fr; border: solid green; }
    #btn_run { margin-top: 1; }
    """

    def __init__(self, parser: argparse.ArgumentParser):
        super().__init__()
        self.parser = parser
        self.inputs = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="form-container", id="form-container"):
            for action in self.parser._actions:
                if action.dest in ('help', 'version', 'tui'):
                    continue
                
                label = action.dest
                
                if isinstance(action, argparse._StoreTrueAction):
                    cb = Checkbox(label, id=f"input_{action.dest}", value=action.default)
                    self.inputs[action.dest] = cb
                    yield cb
                elif action.choices:
                    options = [(str(c), str(c)) for c in action.choices]
                    sel = Select(options, prompt=label, id=f"input_{action.dest}")
                    if action.default:
                        sel.value = str(action.default)
                    self.inputs[action.dest] = sel
                    yield sel
                else:
                    default_val = str(action.default) if action.default is not None else ""
                    # Handle lists like thumbnail_size
                    if isinstance(action.default, list):
                        default_val = ",".join(map(str, action.default))
                    inp = Input(placeholder=label, value=default_val, id=f"input_{action.dest}")
                    self.inputs[action.dest] = inp
                    yield inp
            yield Button("Run", id="btn_run", variant="success")
        
        with Vertical(classes="log-container"):
            yield TextualProgressBar(id="progress_bar", show_eta=False)
            yield RichLog(id="log_view", markup=True)
            
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_run":
            self.query_one("#form-container").disabled = True
            
            # Construct namespace
            args_dict = {}
            for dest, widget in self.inputs.items():
                if isinstance(widget, Checkbox):
                    args_dict[dest] = widget.value
                elif isinstance(widget, Select):
                    # Handle empty select correctly
                    args_dict[dest] = widget.value if widget.value != Select.BLANK else None
                elif isinstance(widget, Input):
                    val = widget.value
                    if dest == 'thumbnail_size': # Special case for nargs=2 integer list
                        try:
                            args_dict[dest] = [int(x.strip()) for x in val.split(",")]
                        except:
                            args_dict[dest] = [800, 600]
                    else:
                        args_dict[dest] = val if val else None
                        
            namespace = argparse.Namespace(**args_dict)
            self.run_processing(namespace)

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
