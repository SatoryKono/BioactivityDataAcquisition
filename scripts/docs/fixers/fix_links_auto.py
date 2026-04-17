#!/usr/bin/env python3
"""Package entrypoint for automatic docs link fixes."""

from __future__ import annotations

from scripts.docs.fix_doc_links_auto import fix_links


def main() -> int:
    fix_links()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
