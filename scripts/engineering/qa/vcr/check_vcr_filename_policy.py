#!/usr/bin/env python3
"""Enforce VCR cassette filename policy for tests/fixtures/vcr."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
VCR_ROOT = ROOT / "tests" / "fixtures" / "vcr"
ALLOWLIST_FILE = ROOT / ".github" / "vcr-noext-allowlist.txt"


def _read_allowlist() -> set[str]:
    if not ALLOWLIST_FILE.exists():
        raise FileNotFoundError(f"Allowlist not found: {ALLOWLIST_FILE}")
    entries: set[str] = set()
    with ALLOWLIST_FILE.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            entries.add(line)
    return entries


def _collect_extensionless_cassettes() -> set[str]:
    if not VCR_ROOT.exists():
        return set()
    result: set[str] = set()
    for path in VCR_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.name == ".gitkeep":
            continue
        if "." in path.name:
            continue
        result.add(path.relative_to(ROOT).as_posix())
    return result


def main() -> int:
    try:
        allowlist = _read_allowlist()
    except OSError as exc:
        sys.stderr.write(f"ERROR: failed to read allowlist: {exc}\n")
        return 2

    extensionless = _collect_extensionless_cassettes()
    unexpected = sorted(extensionless - allowlist)
    stale_allowlist = sorted(allowlist - extensionless)

    if unexpected:
        sys.stderr.write(
            "ERROR: found non-allowlisted VCR files without .yaml extension.\n"
            "Rename to .yaml (preferred) or explicitly add to "
            ".github/vcr-noext-allowlist.txt if intentional.\n"
        )
        for path in unexpected:
            sys.stderr.write(f"  - {path}\n")
        return 1

    if stale_allowlist:
        sys.stdout.write(
            "INFO: stale entries in .github/vcr-noext-allowlist.txt (can be removed):\n"
        )
        for path in stale_allowlist:
            sys.stdout.write(f"  - {path}\n")

    sys.stdout.write(
        "OK: VCR filename policy passed "
        f"({len(extensionless)} legacy extensionless files allowlisted).\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
