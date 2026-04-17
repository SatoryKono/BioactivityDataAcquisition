#!/usr/bin/env python3
"""Package entrypoint for docstring coverage checks."""

from __future__ import annotations

from scripts.docs.check_docstring_coverage import main


if __name__ == "__main__":
    raise SystemExit(main())
