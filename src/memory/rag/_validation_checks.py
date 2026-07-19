"""Internal semantic checks for RAG manifest validation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from memory.rag._validation_model import (
    SHA256_PATTERN,
    SUPPORTED_BUILD_SCOPES,
    RagValidationIssue,
    capture_rag_source_identity,
    normalize_rag_source_path,
)
from memory.rag.chunking import content_hash
from memory.rag.filters import DEFAULT_SELECTED_SOURCE_IDS, iter_rag_sources


def add_issue(
    issues: list[RagValidationIssue],
    code: str,
    path: str,
    message: str,
) -> None:
    """Append one normalized validation issue."""
    issues.append(RagValidationIssue(code=code, path=path, message=message))


def catalog_sources(
    catalog: dict[str, Any],
    issues: list[RagValidationIssue],
) -> dict[str, dict[str, Any]]:
    """Validate and index catalog sources by physical path."""
    raw_sources = catalog.get("sources")
    if not isinstance(raw_sources, list):
        add_issue(issues, "invalid_catalog", "catalog.sources", "sources must be a list")
        return {}

    sources: dict[str, dict[str, Any]] = {}
    for index, raw_source in enumerate(raw_sources):
        issue_path = f"catalog.sources[{index}]"
        if not isinstance(raw_source, dict):
            add_issue(issues, "invalid_catalog_source", issue_path, "source must be an object")
            continue
        raw_path = raw_source.get("source_path")
        if not isinstance(raw_path, str):
            add_issue(issues, "invalid_source_path", issue_path, "source_path must be a string")
            continue
        try:
            normalized = normalize_rag_source_path(
                raw_path,
                allow_virtual_fragment=False,
            )
        except ValueError as exc:
            add_issue(issues, "invalid_source_path", issue_path, str(exc))
            continue
        if normalized in sources:
            add_issue(
                issues,
                "duplicate_catalog_source",
                issue_path,
                f"duplicate catalog source: {normalized}",
            )
            continue
        sources[normalized] = raw_source
    return sources


def validate_catalog_metadata(
    catalog: dict[str, Any],
    issues: list[RagValidationIssue],
    *,
    require_build_scope: str | None,
) -> str | None:
    """Validate top-level schema and return normalized build scope."""
    build_scope = catalog.get("build_scope")
    if not isinstance(build_scope, str) or build_scope not in SUPPORTED_BUILD_SCOPES:
        add_issue(
            issues,
            "invalid_build_scope",
            "catalog.build_scope",
            f"build_scope must be one of {sorted(SUPPORTED_BUILD_SCOPES)}",
        )
        normalized_scope = None
    else:
        normalized_scope = build_scope
    if require_build_scope is not None and build_scope != require_build_scope:
        add_issue(
            issues,
            "build_scope_mismatch",
            "catalog.build_scope",
            f"required {require_build_scope!r}, found {build_scope!r}",
        )

    generator_version = catalog.get("generator_version")
    if not isinstance(generator_version, int) or isinstance(generator_version, bool):
        add_issue(
            issues,
            "invalid_generator_version",
            "catalog.generator_version",
            "generator_version must be an integer",
        )
    git_head_sha = catalog.get("git_head_sha")
    if git_head_sha is not None and not (
        isinstance(git_head_sha, str)
        and re.fullmatch(r"[0-9a-f]{40,64}", git_head_sha)
    ):
        add_issue(
            issues,
            "invalid_source_identity",
            "catalog.git_head_sha",
            "git_head_sha must be null or a lowercase Git object id",
        )
    source_hash = catalog.get("source_surface_sha256")
    if not isinstance(source_hash, str) or not SHA256_PATTERN.fullmatch(source_hash):
        add_issue(
            issues,
            "invalid_source_identity",
            "catalog.source_surface_sha256",
            "source_surface_sha256 must be a lowercase SHA-256 digest",
        )
    if catalog.get("working_tree_state") not in {"clean", "dirty", "unavailable"}:
        add_issue(
            issues,
            "invalid_source_identity",
            "catalog.working_tree_state",
            "working_tree_state must be clean, dirty, or unavailable",
        )
    return normalized_scope


def validate_source_files(
    root: Path,
    sources: dict[str, dict[str, Any]],
    issues: list[RagValidationIssue],
) -> tuple[set[str], set[str]]:
    """Validate current existence and content hash for unique sources."""
    missing_paths: set[str] = set()
    content_stale_paths: set[str] = set()
    resolved_root = root.resolve()
    for source_path, source in sources.items():
        candidate = (resolved_root / source_path).resolve()
        if not candidate.is_relative_to(resolved_root):
            missing_paths.add(source_path)
            add_issue(
                issues,
                "invalid_source_path",
                source_path,
                "resolved source path escapes repository root",
            )
            continue
        if not candidate.is_file():
            missing_paths.add(source_path)
            add_issue(
                issues,
                "missing_source_path",
                source_path,
                "catalog source does not exist",
            )
            continue
        actual_hash = content_hash(candidate.read_text(encoding="utf-8"))
        if source.get("content_hash") != actual_hash:
            content_stale_paths.add(source_path)
            add_issue(
                issues,
                "source_content_mismatch",
                source_path,
                "catalog content_hash does not match current source content",
            )
    return missing_paths, content_stale_paths


def validate_chunks(
    chunks: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    issues: list[RagValidationIssue],
) -> tuple[dict[str, int], dict[int, str | None], set[int]]:
    """Validate chunk identities, source ownership, and content hashes."""
    seen_ids: set[str] = set()
    chunks_by_source: dict[str, int] = {}
    chunk_sources: dict[int, str | None] = {}
    stale_indices: set[int] = set()
    for index, chunk in enumerate(chunks):
        issue_path = f"chunks[{index}]"
        if not isinstance(chunk, dict):
            chunk_sources[index] = None
            stale_indices.add(index)
            add_issue(issues, "invalid_chunk", issue_path, "chunk must be an object")
            continue
        chunk_id = chunk.get("id")
        if not isinstance(chunk_id, str) or not chunk_id:
            add_issue(issues, "invalid_chunk_id", issue_path, "id must be a non-empty string")
        elif chunk_id in seen_ids:
            stale_indices.add(index)
            add_issue(issues, "duplicate_chunk_id", issue_path, f"duplicate chunk id: {chunk_id}")
        else:
            seen_ids.add(chunk_id)

        raw_source_path = chunk.get("source_path")
        if not isinstance(raw_source_path, str):
            chunk_sources[index] = None
            stale_indices.add(index)
            add_issue(issues, "invalid_source_path", issue_path, "source_path must be a string")
        else:
            try:
                source_path = normalize_rag_source_path(
                    raw_source_path,
                    allow_virtual_fragment=True,
                )
            except ValueError as exc:
                chunk_sources[index] = None
                stale_indices.add(index)
                add_issue(issues, "invalid_source_path", issue_path, str(exc))
            else:
                chunk_sources[index] = source_path
                chunks_by_source[source_path] = chunks_by_source.get(source_path, 0) + 1
                if source_path not in sources:
                    stale_indices.add(index)
                    add_issue(
                        issues,
                        "chunk_source_not_cataloged",
                        issue_path,
                        f"chunk source is absent from catalog: {source_path}",
                    )

        chunk_content = chunk.get("content")
        chunk_hash = chunk.get("content_hash")
        if not isinstance(chunk_content, str) or not isinstance(chunk_hash, str):
            stale_indices.add(index)
            add_issue(
                issues,
                "invalid_chunk_content",
                issue_path,
                "content and content_hash must be strings",
            )
        elif content_hash(chunk_content) != chunk_hash:
            stale_indices.add(index)
            add_issue(
                issues,
                "chunk_content_hash_mismatch",
                issue_path,
                "chunk content_hash does not match content",
            )
    return chunks_by_source, chunk_sources, stale_indices


def validate_counts(
    catalog: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    chunks: list[dict[str, Any]],
    chunks_by_source: dict[str, int],
    issues: list[RagValidationIssue],
) -> None:
    """Validate declared source, chunk, and per-source section counts."""
    raw_sources = catalog.get("sources")
    actual_source_count = len(raw_sources) if isinstance(raw_sources, list) else 0
    if catalog.get("source_count") != actual_source_count:
        add_issue(
            issues,
            "source_count_mismatch",
            "catalog.source_count",
            "declared source_count does not match catalog sources",
        )
    if catalog.get("chunk_count") != len(chunks):
        add_issue(
            issues,
            "chunk_count_mismatch",
            "catalog.chunk_count",
            "declared chunk_count does not match chunk rows",
        )
    for source_path, source in sources.items():
        if source.get("section_count") != chunks_by_source.get(source_path, 0):
            add_issue(
                issues,
                "section_count_mismatch",
                source_path,
                "catalog section_count does not match source chunk rows",
            )


def current_eligible_sources(root: Path) -> set[str]:
    """Return the current dynamic full-corpus source set."""
    return {
        normalize_rag_source_path(path.as_posix(), allow_virtual_fragment=False)
        for path in iter_rag_sources(
            root,
            selected_ids=DEFAULT_SELECTED_SOURCE_IDS,
            workflow_focus_query=None,
            max_sources=None,
        )
    }


def validate_source_identity(
    root: Path,
    catalog: dict[str, Any],
    identity_sources: set[str],
    issues: list[RagValidationIssue],
) -> tuple[str | None, bool]:
    """Compare catalog source identity with the current source surface."""
    try:
        current_identity = capture_rag_source_identity(root, identity_sources)
    except (OSError, UnicodeError, ValueError):
        return None, False
    current_hash = current_identity["source_surface_sha256"]
    identity_mismatch = catalog.get("source_surface_sha256") != current_hash
    catalog_head = catalog.get("git_head_sha")
    current_head = current_identity["git_head_sha"]
    if catalog_head is not None and current_head is not None and catalog_head != current_head:
        identity_mismatch = True
    if identity_mismatch:
        add_issue(
            issues,
            "source_identity_mismatch",
            "catalog.source_surface_sha256",
            "catalog source snapshot does not match the current repository surface",
        )
    return current_hash if isinstance(current_hash, str) else None, identity_mismatch
