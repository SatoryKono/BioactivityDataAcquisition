"""Markdown-aware chunking for deterministic project-memory manifests."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
FRONTMATTER_DELIMITER = "---"


@dataclass(frozen=True, slots=True)
class ChunkSection:
    """Represents a deterministic chunk section extracted from a markdown file."""

    index: int
    title: str
    level: int
    content: str


def _strip_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if len(lines) >= 3 and lines[0].strip() == FRONTMATTER_DELIMITER:
        for idx in range(1, len(lines)):
            if lines[idx].strip() == FRONTMATTER_DELIMITER:
                return "\n".join(lines[idx + 1 :]).lstrip("\n")
    return text


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "section"


def split_markdown_sections(text: str) -> list[ChunkSection]:
    """Split markdown text into section chunks using heading boundaries."""
    body = _strip_frontmatter(text).strip()
    if not body:
        return []

    sections: list[ChunkSection] = []
    current_title = "preamble"
    current_level = 0
    current_lines: list[str] = []
    current_index = 0

    for line in body.splitlines():
        match = HEADING_PATTERN.match(line)
        if match:
            content = "\n".join(current_lines).strip()
            if content:
                sections.append(
                    ChunkSection(
                        index=current_index,
                        title=current_title,
                        level=current_level,
                        content=content,
                    )
                )
                current_index += 1
            current_title = match.group(2).strip()
            current_level = len(match.group(1))
            current_lines = [line]
            continue
        current_lines.append(line)

    content = "\n".join(current_lines).strip()
    if content:
        sections.append(
            ChunkSection(
                index=current_index,
                title=current_title,
                level=current_level,
                content=content,
            )
        )
    return sections


def content_hash(text: str) -> str:
    """Return a stable SHA-256 content hash for a text payload."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_chunk_id(source_path: str, title: str, index: int) -> str:
    """Build a deterministic chunk identifier from source path and section title."""
    digest = hashlib.sha1(f"{source_path}:{index}:{title}".encode("utf-8")).hexdigest()[:12]
    return f"{source_path}#{_slugify(title)}-{digest}"


def infer_source_type(path: Path) -> str:
    """Classify a repository markdown file into a RAG source type."""
    normalized = path.as_posix()
    if normalized.startswith("docs/02-architecture/decisions/ADR-"):
        return "adr"
    if normalized.startswith("docs/05-operations/runbooks/"):
        return "runbook"
    return "doc"


def infer_domain(path: Path) -> str:
    """Infer a coarse domain label from a repository markdown path."""
    normalized = path.as_posix()
    if normalized.startswith("docs/02-architecture/"):
        return "architecture"
    if normalized.startswith("docs/05-operations/"):
        return "operations"
    return "project"
