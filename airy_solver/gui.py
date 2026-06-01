"""Compatibility wrapper so `python -m airy_solver.gui` works from this folder."""

from __future__ import annotations

import pathlib
import sys


_PARENT = pathlib.Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from gui import run_gui  # noqa: E402


if __name__ == "__main__":
    run_gui()
