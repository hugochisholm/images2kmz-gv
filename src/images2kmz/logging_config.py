"""Logging configuration for images2kmz.

Provides dual logging:
- Console output (--verbose): INFO, WARNING, ERROR
- File output (--log-file): DEBUG, INFO, WARNING, ERROR
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


# ISO 8601 timestamp format
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"

# Console format: clean, readable
CONSOLE_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

# File format: detailed with context for debugging
FILE_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
)


def setup_logging(
    *,
    verbose: bool = False,
    log_file: Path | str | None = None,
) -> None:
    """Configure logging for images2kmz.

    Sets up dual logging:
    - Console: INFO+ if verbose=True, WARNING+ otherwise
    - File: DEBUG+ if log_file is specified

    Args:
        verbose: Enable console output at INFO level and above
        log_file: Path to log file for DEBUG+ output
    """
    # Remove any existing handlers to start fresh
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set root logger level to DEBUG to allow all messages through
    root_logger.setLevel(logging.DEBUG)

    # Console handler - controlled by --verbose flag
    console_level = logging.INFO if verbose else logging.WARNING
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter(CONSOLE_FORMAT, datefmt=TIMESTAMP_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler - controlled by --log-file flag
    if log_file:
        log_path = Path(log_file)
        # Ensure parent directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(FILE_FORMAT, datefmt=TIMESTAMP_FORMAT)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        logging.getLogger(__name__).debug(f"Logging to file: {log_path}")

    # Set third-party library log levels to reduce noise
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("simplekml").setLevel(logging.WARNING)
