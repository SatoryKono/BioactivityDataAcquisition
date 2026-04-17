#!/usr/bin/env python3
"""Package entrypoint for sentence-level docs audit."""

from __future__ import annotations

from scripts.docs.sentence_doc_audit import generate


def main() -> int:
    generate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
