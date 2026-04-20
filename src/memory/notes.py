"""Shared markdown note helpers for curated and episodic memory records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

FRONTMATTER_DELIMITER = "---"
SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True, slots=True)
class MemoryNote:
    """Represents one markdown-backed memory note."""

    metadata: dict[str, Any]
    body: str


def utc_now_iso() -> str:
    """Return the current UTC timestamp as an ISO-8601 string with Z suffix."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    """Create a filesystem-safe slug from a title or identifier."""
    slug = SLUG_PATTERN.sub("-", value.strip().lower()).strip("-")
    return slug or "note"


def parse_markdown_note(path: Path) -> MemoryNote:
    """Parse a markdown note with YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith(f"{FRONTMATTER_DELIMITER}\n"):
        raise ValueError(f"note is missing YAML frontmatter: {path}")
    parts = text.split(f"\n{FRONTMATTER_DELIMITER}\n", 1)
    if len(parts) != 2:
        raise ValueError(f"note frontmatter is not terminated: {path}")
    metadata_text = parts[0][len(FRONTMATTER_DELIMITER) + 1 :]
    metadata = yaml.safe_load(metadata_text) or {}
    if not isinstance(metadata, dict):
        raise ValueError(f"note frontmatter must be a mapping: {path}")
    return MemoryNote(metadata=metadata, body=parts[1].lstrip("\n"))


def render_markdown_note(metadata: dict[str, Any], body: str) -> str:
    """Render metadata and body into a markdown note."""
    frontmatter = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=False).strip()
    normalized_body = body.rstrip() + "\n"
    return (
        f"{FRONTMATTER_DELIMITER}\n"
        f"{frontmatter}\n"
        f"{FRONTMATTER_DELIMITER}\n\n"
        f"{normalized_body}"
    )


def write_markdown_note(path: Path, metadata: dict[str, Any], body: str) -> Path:
    """Write a markdown note with YAML frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_note(metadata, body), encoding="utf-8")
    return path
