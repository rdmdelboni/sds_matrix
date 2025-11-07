"""Helpers for discovering document files."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from .config import SUPPORTED_FORMATS


def iter_supported_files(folder: Path) -> Iterable[Path]:
    """Yield supported files contained in the given folder."""
    for entry in folder.iterdir():
        if entry.is_file() and entry.suffix.lower() in SUPPORTED_FORMATS:
            yield entry


def list_supported_files(folder: Path) -> List[Path]:
    """Return a sorted list of supported files in the folder."""
    return sorted(iter_supported_files(folder), key=lambda path: path.name.lower())
