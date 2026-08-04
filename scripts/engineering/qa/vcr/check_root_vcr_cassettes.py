#!/usr/bin/env python3
"""Block VCR cassette anti-patterns in repository."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
VCR_ROOT = ROOT / "tests" / "fixtures" / "vcr"
LEGACY_VCR_ROOT = ROOT / "tests" / "fixtures" / "vcr_cassettes"


def _looks_like_vcr_cassette(path: Path) -> bool:
    """Return True when file starts with VCR interactions header."""
    try:
        with path.open(encoding="utf-8") as handle:
            first_non_empty = ""
            for raw_line in handle:
                line = raw_line.strip()
                if line:
                    first_non_empty = line
                    break
            return first_non_empty == "interactions:"
    except UnicodeDecodeError:
        return False


def get_root_vcr_cassettes() -> list[Path]:
    """Return root-level files that look like VCR cassettes."""
    cassettes: list[Path] = []
    for path in ROOT.iterdir():
        if not path.is_file() or path.suffix not in {"", ".yaml"}:
            continue
        if _looks_like_vcr_cassette(path):
            cassettes.append(path)

    return sorted(cassettes)


def get_legacy_from_root_markers() -> list[Path]:
    """Return migrated-but-unconsolidated cassettes (*.from_root.yaml)."""
    if not VCR_ROOT.exists():
        return []
    return sorted(VCR_ROOT.rglob("*.from_root.yaml"))


def get_legacy_vcr_cassettes_files() -> list[Path]:
    """Return files under legacy fixtures/vcr_cassettes directory."""
    if not LEGACY_VCR_ROOT.exists():
        return []
    return sorted(path for path in LEGACY_VCR_ROOT.rglob("*") if path.is_file())


def get_noncanonical_test_vcr_cassettes() -> list[Path]:
    """Return VCR cassettes under tests/ outside the canonical fixtures/vcr tree.

    Issue #4468: shadow cassettes under tests/integration/**/cassettes must not
    reappear beside the managed catalog under tests/fixtures/vcr.
    """
    tests_root = ROOT / "tests"
    if not tests_root.is_dir():
        return []
    noncanonical: list[Path] = []
    for path in tests_root.rglob("*.yaml"):
        if not path.is_file():
            continue
        try:
            relative = path.relative_to(ROOT)
        except ValueError:
            continue
        parts = relative.parts
        # Canonical managed inventory lives only under tests/fixtures/vcr/**
        if len(parts) >= 3 and parts[0] == "tests" and parts[1] == "fixtures":
            if len(parts) >= 3 and parts[2] == "vcr":
                continue
            if len(parts) >= 3 and parts[2] == "vcr_cassettes":
                # handled by get_legacy_vcr_cassettes_files
                continue
        if path.name.endswith("_meta.yaml"):
            continue
        if _looks_like_vcr_cassette(path):
            noncanonical.append(path)
    return sorted(noncanonical)


def main() -> int:
    """Run check and report violations."""
    invalid_cassettes = get_root_vcr_cassettes()
    legacy_from_root = get_legacy_from_root_markers()
    legacy_vcr_cassettes = get_legacy_vcr_cassettes_files()
    noncanonical_test_cassettes = get_noncanonical_test_vcr_cassettes()
    if (
        not invalid_cassettes
        and not legacy_from_root
        and not legacy_vcr_cassettes
        and not noncanonical_test_cassettes
    ):
        sys.stdout.write("No VCR cassette anti-patterns detected.\n")
        return 0

    if invalid_cassettes:
        sys.stdout.write(
            "Found root-level VCR cassette files. Move them to tests/fixtures/vcr/<provider>/:\n"
        )
        for cassette in invalid_cassettes:
            sys.stdout.write(f" - {cassette.name}\n")
    if legacy_from_root:
        sys.stdout.write(
            "Found legacy '*.from_root.yaml' VCR files. Consolidate to canonical cassette names:\n"
        )
        for cassette in legacy_from_root:
            sys.stdout.write(f" - {cassette.relative_to(ROOT)}\n")
    if legacy_vcr_cassettes:
        sys.stdout.write(
            "Found files under legacy tests/fixtures/vcr_cassettes/. Move them under tests/fixtures/vcr/<provider>/:\n"
        )
        for cassette in legacy_vcr_cassettes:
            sys.stdout.write(f" - {cassette.relative_to(ROOT)}\n")
    if noncanonical_test_cassettes:
        sys.stdout.write(
            "Found non-canonical VCR cassettes outside tests/fixtures/vcr/. "
            "Move or delete shadows; keep managed inventory under "
            "tests/fixtures/vcr/<provider>/ (#4468):\n"
        )
        for cassette in noncanonical_test_cassettes:
            sys.stdout.write(f" - {cassette.relative_to(ROOT)}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
