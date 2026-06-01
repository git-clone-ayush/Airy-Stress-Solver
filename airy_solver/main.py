"""Compatibility wrapper so `python -m airy_solver.main` works from this folder."""

from __future__ import annotations

import pathlib
import sys


_PARENT = pathlib.Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from main import main as _root_main, run_solver_pipeline  # noqa: E402


def main():
    _root_main()


if __name__ == "__main__":
    main()