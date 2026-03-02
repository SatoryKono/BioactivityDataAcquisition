#!/usr/bin/env python3
"""Block VCR cassette files from being committed in repository root."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def get_root_vcr_cassettes() -> list[Path]:
    """Return root-level files that look like VCR cassettes."""
    cassettes: list[Path] = []
    for path in ROOT.iterdir():
        if not path.is_file() or path.suffix:
            continue
        try:
            with path.open(encoding="utf-8") as handle:
                first_non_empty = ""
                for raw_line in handle:
                    line = raw_line.strip()
                    if line:
                        first_non_empty = line
                        break
                if first_non_empty == "interactions:":
                    cassettes.append(path)
        except UnicodeDecodeError:
            continue

    return sorted(cassettes)


def main() -> int:
    """Run check and report violations."""
    invalid_cassettes = get_root_vcr_cassettes()
    if not invalid_cassettes:
        sys.stdout.write("No root-level VCR cassettes detected.\n")
        return 0

    sys.stdout.write(
        "Found root-level VCR cassette files. Move them to tests/fixtures/vcr/<provider>/:\n"
    )
    for cassette in invalid_cassettes:
        sys.stdout.write(f" - {cassette.name}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
