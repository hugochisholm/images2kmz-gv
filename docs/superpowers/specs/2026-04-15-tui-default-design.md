# Design Spec: images2kmz Entry Point Logic

**Date:** 2026-04-15
**Topic:** TUI by default on no-args

## Context
Currently, `images2kmz` requires a `--tui` flag to launch the Textual User Interface. Running the command without arguments triggers a CLI prompt for a directory.

## Goal
Modify the entry point so that:
1.  Running with no arguments starts the TUI.
2.  Running with the `--tui` flag (and any other arguments) starts the TUI.
3.  Running with any arguments (but no `--tui` flag) starts the standard CLI behavior.

## Design

### Dispatch Logic
The dispatch logic will be centralized in `src/images2kmz/cli.py` within the `run()` function.

```python
def run(args: list | None = None) -> int:
    # ...
    # Determine effective arguments passed to the script
    effective_args = args if args is not None else sys.argv[1:]
    
    # Parse arguments
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    # Launch TUI if:
    # 1. Explicitly requested via --tui flag
    # 2. No arguments were provided at all
    if parsed_args.tui or not effective_args:
        from .tui import run_tui
        return run_tui(parser)
    
    # ... rest of CLI logic
```

### Affected Files
- `src/images2kmz/cli.py`: Update `run()` function to include the new dispatch condition.

## Verification

### Manual Tests
- `python -m images2kmz`: Should launch TUI.
- `python -m images2kmz --tui`: Should launch TUI.
- `python -m images2kmz .`: Should run CLI on current directory.
- `python -m images2kmz --help`: Should show CLI help.

### Automated Tests
- Mock `run_tui` in `tests/test_cli.py` and verify it is called when `run([])` is invoked.
