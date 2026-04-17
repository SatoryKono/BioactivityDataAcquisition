#!/usr/bin/env python3
"""Package entrypoint for explicit docs link fixes."""

from __future__ import annotations

from scripts.docs.fix_doc_links_explicit import fix_all_broken_links


def main() -> int:
    fix_all_broken_links()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
