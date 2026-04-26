"""Shared markdown note helpers for curated and episodic memory records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

FRONTMATTER_DELIMITER = "---"
LEGACY_FRONTMATTER_DELIMITER_PATTERN = re.compile(r"^_{3,}$")
LEGACY_INDENTED_TOP_LEVEL_KEY_PATTERN = re.compile(
    r"^\s{2,}(confidence|last_verified|summary|query|kind):"
)
SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


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


def normalize_text_key(value: str) -> str:
    """Normalize a text key for duplicate detection and loose comparisons."""
    return " ".join(value.strip().lower().split())


def parse_markdown_note(path: Path) -> MemoryNote:
    """Parse a markdown note with YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines:
        raise ValueError(f"note is missing YAML frontmatter: {path}")
    first_line = lines[0].strip()
    if first_line != FRONTMATTER_DELIMITER and not LEGACY_FRONTMATTER_DELIMITER_PATTERN.match(
        first_line
    ):
        raise ValueError(f"note is missing YAML frontmatter: {path}")

    delimiter = first_line
    end_index: int | None = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == delimiter:
            end_index = idx
            break
    if end_index is None:
        raise ValueError(f"note frontmatter is not terminated: {path}")

    metadata_text = "".join(lines[1:end_index])
    metadata = _load_frontmatter_metadata(metadata_text)
    if not isinstance(metadata, dict):
        raise ValueError(f"note frontmatter must be a mapping: {path}")
    body = "".join(lines[end_index + 1 :]).lstrip("\n")
    return MemoryNote(metadata=metadata, body=body)


def _load_frontmatter_metadata(metadata_text: str) -> dict[str, Any]:
    """Parse note frontmatter with compatibility fallback for legacy malformed notes."""
    try:
        loaded = yaml.safe_load(metadata_text) or {}
    except yaml.YAMLError:
        normalized_lines = []
        for line in metadata_text.splitlines():
            if LEGACY_INDENTED_TOP_LEVEL_KEY_PATTERN.match(line):
                normalized_lines.append(line.lstrip())
            else:
                normalized_lines.append(line)
        loaded = yaml.safe_load("\n".join(normalized_lines)) or {}
    if not isinstance(loaded, dict):
        raise ValueError("note frontmatter must be a mapping")
    ttl_days = loaded.get("ttl_days")
    if isinstance(ttl_days, str) and ttl_days.isdigit():
        loaded["ttl_days"] = int(ttl_days)
    return loaded


def extract_markdown_headings(body: str) -> list[str]:
    """Return markdown headings in their rendered form."""
    headings: list[str] = []
    for match in HEADING_PATTERN.finditer(body):
        level_marks, title = match.groups()
        headings.append(f"{level_marks} {title.strip()}")
    return headings


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
