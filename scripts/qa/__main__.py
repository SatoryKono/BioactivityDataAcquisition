#!/usr/bin/env python3
"""Compatibility entry point for ``python -m scripts.qa``."""

from __future__ import annotations

from scripts.engineering.qa.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main())
