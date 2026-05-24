"""Shared markdown note helpers for curated and episodic memory records."""

from __future__ import annotations

import re
import threading
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


def _open_with_timeout(path: Path, timeout: float):
    """Open a file with a timeout to prevent hangs on network drives."""
    handle = None
    exception = None

    def _target():
        nonlocal handle, exception
        try:
            handle = path.open("r", encoding="utf-8")
        except Exception as e:
            exception = e

    thread = threading.Thread(target=_target)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        raise TimeoutError(f"File open did not complete within {timeout} seconds: {path}")

    if exception is not None:
        raise exception

    return handle


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


def parse_markdown_note(path: Path, *, include_body: bool = True) -> MemoryNote:
    """Parse a markdown note with YAML frontmatter."""
    try:
        handle = _open_with_timeout(path, timeout=5.0)
    except (OSError, TimeoutError) as exc:
        raise ValueError(f"failed to open note file: {exc}") from exc
    with handle:
        first_line = handle.readline()
        if not first_line:
            raise ValueError(f"note is missing YAML frontmatter: {path}")
        first_line = first_line.strip()
        if (
            first_line != FRONTMATTER_DELIMITER
            and not LEGACY_FRONTMATTER_DELIMITER_PATTERN.match(first_line)
        ):
            raise ValueError(f"note is missing YAML frontmatter: {path}")

        delimiter = first_line
        if not include_body:
            metadata = _read_frontmatter_metadata_only(handle, delimiter, path)
            return MemoryNote(metadata=metadata, body="")
        metadata_lines: list[str] = []
        for line in handle:
            if line.strip() == delimiter:
                metadata_text = "".join(metadata_lines)
                metadata = _load_frontmatter_metadata(metadata_text)
                if not isinstance(metadata, dict):
                    raise ValueError(f"note frontmatter must be a mapping: {path}")
                body = handle.read().lstrip("\n") if include_body else ""
                return MemoryNote(metadata=metadata, body=body)
            metadata_lines.append(line)

    raise ValueError(f"note frontmatter is not terminated: {path}")


def _read_frontmatter_metadata_only(
    handle: Any,
    delimiter: str,
    path: Path,
) -> dict[str, Any]:
    """Parse simple frontmatter fields without loading the note body."""
    metadata: dict[str, Any] = {}
    current_list_key: str | None = None

    for line in handle:
        stripped = line.strip()
        if stripped == delimiter:
            ttl_days = metadata.get("ttl_days")
            if isinstance(ttl_days, str) and ttl_days.isdigit():
                metadata["ttl_days"] = int(ttl_days)
            return metadata
        if not stripped:
            continue
        if stripped.startswith("- ") and current_list_key is not None:
            metadata[current_list_key].append(_coerce_frontmatter_scalar(stripped[2:]))
            continue
        if ":" not in line:
            current_list_key = None
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            current_list_key = None
            continue
        if not value:
            metadata[key] = []
            current_list_key = key
            continue
        metadata[key] = _coerce_frontmatter_scalar(value)
        current_list_key = None

    raise ValueError(f"note frontmatter is not terminated: {path}")


def _coerce_frontmatter_scalar(value: str) -> Any:
    """Coerce simple YAML scalar values used in note frontmatter."""
    normalized = value.strip()
    was_quoted = (
        len(normalized) >= 2
        and normalized[0] == normalized[-1]
        and normalized[0] in {'"', "'"}
    )
    if was_quoted:
        return normalized[1:-1]
    if normalized in {"null", "~"}:
        return None
    if normalized.isdigit():
        return int(normalized)
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return normalized


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
