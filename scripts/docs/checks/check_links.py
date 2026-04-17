#!/usr/bin/env python3
"""Package entrypoint for documentation link checks."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.docs.check_doc_links import main


if __name__ == "__main__":
    raise SystemExit(main())
