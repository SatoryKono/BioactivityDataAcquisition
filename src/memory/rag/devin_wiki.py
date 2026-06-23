"""Derived chunk builder for the repository's Devin navigation wiki."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from memory.graph.refs import graph_refs_for_source, related_refs_for_source
from memory.rag.chunking import build_chunk_id, content_hash


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "page"


def _string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    rendered: list[str] = []
    for item in values:
        if isinstance(item, str) and item.strip():
            rendered.append(item.strip())
        elif isinstance(item, dict):
            content = item.get("content")
            if isinstance(content, str) and content.strip():
                rendered.append(content.strip())
    return rendered


def _page_source_path(source_path: str, title: str) -> str:
    return f"{source_path}#{_slugify(title)}"


def _page_content(page: dict[str, Any]) -> str:
    title = str(page.get("title") or "Untitled page").strip()
    purpose = str(page.get("purpose") or "").strip()
    parent = str(page.get("parent") or "").strip()
    notes = _string_list(page.get("page_notes"))

    lines = [f"Title: {title}"]
    if purpose:
        lines.extend(["", f"Purpose: {purpose}"])
    if parent:
        lines.extend(["", f"Parent: {parent}"])
    if notes:
        lines.extend(["", "Notes:"])
        lines.extend(f"- {note}" for note in notes)
    return "\n".join(lines)


def _repo_notes_content(notes: object) -> str | None:
    entries = _string_list(notes)
    if not entries:
        return None
    return "Repo notes:\n" + "\n".join(f"- {entry}" for entry in entries)


def build_devin_wiki_records(
    root: Path,
    rel_path: Path,
    *,
    owner: str,
    repo_zone: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build deterministic corpus and chunk records from .devin/wiki.json."""
    source_path = rel_path.as_posix()
    text = (root / rel_path).read_text(encoding="utf-8")
    payload = json.loads(text)

    base_graph_refs = graph_refs_for_source(source_path, "devin_wiki")
    base_related_refs = related_refs_for_source(source_path, "devin_wiki")
    chunks: list[dict[str, Any]] = []
    index = 0

    repo_notes_content = _repo_notes_content(payload.get("repo_notes"))
    if repo_notes_content:
        virtual_path = f"{source_path}#repo-notes"
        chunks.append(
            {
                "id": build_chunk_id(source_path, "repo-notes", index),
                "source_path": virtual_path,
                "source_type": "devin_wiki",
                "domain": "project",
                "repo_zone": repo_zone,
                "title": "repo-notes",
                "heading_level": 1,
                "symbol": "repo-notes",
                "symbol_kind": "wiki_repo_notes",
                "content": repo_notes_content,
                "content_hash": content_hash(repo_notes_content),
                "graph_node_refs": base_graph_refs,
                "related_refs": [*base_related_refs, "devin-wiki-section::repo-notes"],
                "owner": owner,
                "freshness_class": "warm",
                "confidence": "derived",
            }
        )
        index += 1

    for page in payload.get("pages", []):
        if not isinstance(page, dict):
            continue
        title = str(page.get("title") or "").strip()
        if not title:
            continue
        virtual_path = _page_source_path(source_path, title)
        parent = str(page.get("parent") or "").strip()
        page_related_refs = [*base_related_refs, f"devin-wiki-page::{_slugify(title)}"]
        if parent:
            page_related_refs.append(f"devin-wiki-parent::{_slugify(parent)}")
        page_content = _page_content(page)
        chunks.append(
            {
                "id": build_chunk_id(source_path, title, index),
                "source_path": virtual_path,
                "source_type": "devin_wiki",
                "domain": "project",
                "repo_zone": repo_zone,
                "title": title,
                "heading_level": 1,
                "symbol": title,
                "symbol_kind": "wiki_page",
                "content": page_content,
                "content_hash": content_hash(page_content),
                "graph_node_refs": base_graph_refs,
                "related_refs": page_related_refs,
                "owner": owner,
                "freshness_class": "warm",
                "confidence": "derived",
            }
        )
        index += 1

    catalog = {
        "source_path": source_path,
        "source_type": "devin_wiki",
        "domain": "project",
        "repo_zone": repo_zone,
        "owner": owner,
        "content_hash": content_hash(text),
        "section_count": len(chunks),
    }
    return catalog, chunks
