#!/usr/bin/env python3
"""Package entrypoint for documentation link checks."""

from __future__ import annotations

from scripts.docs.check_doc_links import main


if __name__ == "__main__":
    raise SystemExit(main())
