#!/usr/bin/env python3
"""Package entrypoint for documentation drift checks."""

from __future__ import annotations

from scripts.docs.check_doc_drift import main


if __name__ == "__main__":
    raise SystemExit(main())
