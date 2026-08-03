"""ADR file utility functions for filesystem operations."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

ADR_FILENAME_RE = re.compile(r"^ADR-(\d+)-(.+)\.md$", re.IGNORECASE)


def iter_adr_files(base_dir: Path) -> Iterable[Path]:
    """Iterate over ADR markdown files in the given directory.

    Args:
        base_dir: Directory to search for ADR files.

    Returns:
        Sorted list of ADR file paths.
    """
    if not base_dir.exists():
        return []
    # Sort for deterministic order
    return sorted(p for p in base_dir.glob("ADR-*.md") if p.is_file())


def parse_adr_filename(path: Path) -> tuple[int, str] | None:
    """Parse ADR filename to extract number and title.

    Args:
        path: Path to ADR file.

    Returns:
        Tuple of (number, title) or None if filename doesn't match pattern.
    """
    m = ADR_FILENAME_RE.match(path.name)
    if not m:
        return None
    num = int(m.group(1))
    title = m.group(2).replace("-", " ")
    return num, title


def find_adr_by_number(base_dir: Path, number: int) -> Path | None:
    """Find ADR file by its number.

    Args:
        base_dir: Directory containing ADR files.
        number: ADR number to find.

    Returns:
        Path to ADR file or None if not found.
    """
    pattern = f"ADR-{number:03d}-*.md"
    matches = list(base_dir.glob(pattern))
    if not matches:
        return None
    # If multiple, pick lexicographically first for determinism
    return sorted(matches)[0]
