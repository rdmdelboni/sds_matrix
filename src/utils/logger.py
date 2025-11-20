"""Application-wide logging helpers."""

from __future__ import annotations

import logging
import sys
from typing import Final

from .config import LOG_FILE, LOG_LEVEL

LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

def setup_logger(name: str = "fds_reader") -> logging.Logger:
    """Configure and return a logger with console and file handlers."""
    logger = logging.getLogger(name)
    if logger.handlers:
        # Avoid duplicate handlers when importing across modules.
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

logger = setup_logger()
