"""CLI entry point for launching the FDS Reader GUI."""

from .gui.main_app import run_app


def main() -> None:
    """Start the Tkinter application."""
    run_app()
