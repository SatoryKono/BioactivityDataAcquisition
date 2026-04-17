#!/usr/bin/env python3
"""Package entrypoint for documentation drift checks."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.docs.check_doc_drift import main


if __name__ == "__main__":
    raise SystemExit(main())
