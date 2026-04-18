#!/usr/bin/env python3
"""Legacy compatibility wrapper for the canonical architecture check script."""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> None:
    script = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "engineering"
        / "qa"
        / "check_architecture.py"
    )
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
