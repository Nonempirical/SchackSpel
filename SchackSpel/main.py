"""Program entrypoint that launches the GUI."""

from __future__ import annotations

from gui import main as run_gui


def main() -> int:
    """Launch the graphical application."""
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
