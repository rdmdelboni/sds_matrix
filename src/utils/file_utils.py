"""Helpers for discovering document files."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from .config import SUPPORTED_FORMATS


def iter_supported_files(folder: Path, recursive: bool = True) -> Iterable[Path]:
    """Yield supported files contained in the given folder.

    Args:
        folder: The folder to search for files
        recursive: If True, search in all subdirectories recursively (default: True)
    """
    if recursive:
        # Use rglob for recursive search
        for entry in folder.rglob("*"):
            if entry.is_file() and entry.suffix.lower() in SUPPORTED_FORMATS:
                yield entry
    else:
        # Original behavior: only direct children
        for entry in folder.iterdir():
            if entry.is_file() and entry.suffix.lower() in SUPPORTED_FORMATS:
                yield entry


def list_supported_files(folder: Path, recursive: bool = True) -> List[Path]:
    """Return a sorted list of supported files in the folder.

    Args:
        folder: The folder to search for files
        recursive: If True, search in all subdirectories recursively (default: True)
    """
    return sorted(iter_supported_files(folder, recursive=recursive), key=lambda path: path.name.lower())
