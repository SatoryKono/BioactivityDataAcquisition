"""Tests for the baseline project-memory scaffold validator."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from memory.notes import write_markdown_note
from memory.resources import (
    MEMORY_ROOT,
    REQUIRED_CATALOG_FILES,
    REQUIRED_POLICY_FILES,
    REQUIRED_SCHEMA_FILES,
    iter_catalog_paths,
    iter_policy_paths,
    iter_schema_paths,
)
from memory.validation import (
    _is_tracked_generated_memory_artifact,
    _validate_note_placement,
    validate_memory_scaffold,
)


def test_required_memory_resource_files_exist() -> None:
    assert [path.name for path in iter_policy_paths()] == list(REQUIRED_POLICY_FILES)
    assert [path.name for path in iter_catalog_paths()] == list(REQUIRED_CATALOG_FILES)
    assert [path.name for path in iter_schema_paths()] == list(REQUIRED_SCHEMA_FILES)

    for path in (*iter_policy_paths(), *iter_catalog_paths(), *iter_schema_paths()):
        assert path.exists(), path


def test_memory_scaffold_validation_passes() -> None:
    assert validate_memory_scaffold() == []


def test_memory_scaffold_validation_accepts_valid_note_files(tmp_path: Path) -> None:
    memory_root = tmp_path / "memory"
    shutil.copytree(MEMORY_ROOT, memory_root)

    write_markdown_note(
        memory_root / "curated" / "lessons" / "valid-lesson.md",
        metadata={
            "id": "valid-lesson",
            "title": "Valid lesson",
            "kind": "lesson",
            "source_refs": ["src/memory/README.md"],
            "confidence": "curated",
            "last_verified": "2026-04-20T00:00:00Z",
            "summary": "Durable lesson for repeated reuse.",
        },
        body=(
            "# Lesson\n\n"
            "## Observation\n\n"
            "- Durable guidance\n\n"
            "## Reuse guidance\n\n"
            "- Apply again when the same conditions hold.\n"
        ),
    )
    write_markdown_note(
        memory_root / "episodic" / "sessions" / "valid-session.md",
        metadata={
            "id": "valid-session",
            "title": "Valid session",
            "task_id": "task-123",
            "created_at": "2026-04-20T00:00:00Z",
            "ttl_days": 14,
            "confidence": "episodic",
            "source_refs": ["src/memory/README.md"],
            "summary": "Working context.",
        },
        body="# Session\n\n- Current context\n",
    )

    assert validate_memory_scaffold(memory_root) == []


def test_memory_scaffold_validation_skips_episodic_body_reads(
    tmp_path: Path,
    monkeypatch,
) -> None:
    memory_root = tmp_path / "memory"
    shutil.copytree(MEMORY_ROOT, memory_root)

    write_markdown_note(
        memory_root / "episodic" / "sessions" / "valid-session.md",
        metadata={
            "id": "valid-session",
            "title": "Valid session",
            "task_id": "task-123",
            "created_at": "2026-04-20T00:00:00Z",
            "ttl_days": 14,
            "confidence": "episodic",
            "source_refs": ["src/memory/README.md"],
            "summary": "Working context.",
        },
        body="# Session\n\n- Current context\n",
    )

    original_parse = validate_memory_scaffold.__globals__["parse_markdown_note"]
    include_body_flags: list[bool] = []

    def recording_parse(path: Path, *, include_body: bool = True) -> Any:
        include_body_flags.append(include_body)
        return original_parse(path, include_body=include_body)

    monkeypatch.setitem(
        validate_memory_scaffold.__globals__,
        "parse_markdown_note",
        recording_parse,
    )

    assert validate_memory_scaffold(memory_root) == []
    assert False in include_body_flags


def test_memory_scaffold_validation_bounds_default_episodic_scan(
    memory_local_tmp_path: Path,
    monkeypatch,
) -> None:
    memory_root = memory_local_tmp_path / "memory"
    shutil.copytree(MEMORY_ROOT, memory_root)

    # Patch the limit to a small value to avoid network drive timeouts
    # while still testing the boundary behavior
    monkeypatch.setattr(
        "memory.validation.DEFAULT_EPISODIC_NOTE_SCAN_LIMIT",
        5,
    )

    sessions_dir = memory_root / "episodic" / "sessions"
    for index in range(10):
        write_markdown_note(
            sessions_dir / f"session-{index:03d}.md",
            metadata={
                "id": f"session-{index:03d}",
                "title": f"Session {index:03d}",
                "task_id": f"task-{index:03d}",
                "created_at": "2026-04-20T00:00:00Z",
                "ttl_days": 14,
                "confidence": "episodic",
                "source_refs": ["src/memory/README.md"],
                "summary": "Working context.",
            },
            body="# Session\n\n- Current context\n",
        )

    limited_issues = validate_memory_scaffold(memory_root)
    full_issues = validate_memory_scaffold(memory_root, include_all_episodic_notes=True)

    assert limited_issues == []
    assert full_issues == []


def test_memory_scaffold_validation_flags_invalid_note_files(tmp_path: Path) -> None:
    memory_root = tmp_path / "memory"
    shutil.copytree(MEMORY_ROOT, memory_root)

    write_markdown_note(
        memory_root / "curated" / "lessons" / "broken-lesson.md",
        metadata={
            "id": "broken-lesson",
            "title": "Broken lesson",
            "kind": "lesson",
            "source_refs": ["<add-source-ref>"],
            "confidence": "episodic",
            "summary": "Replace with a durable summary.",
        },
        body="# Lesson\n\n## Observation\n\n- Replace with current findings\n",
    )

    issues = validate_memory_scaffold(memory_root)
    messages = {
        issue.message for issue in issues if issue.path.endswith("broken-lesson.md")
    }
    assert "note missing required field: last_verified" in messages
    assert "note confidence must be 'curated' for curated_note" in messages
    assert "curated note summary contains placeholder text" in messages
    assert "curated note source_refs contain placeholder text" in messages
    assert "curated note body contains placeholder text" in messages
    assert "curated note missing required heading: ## Reuse guidance" in messages


def test_memory_scaffold_validation_flags_duplicate_curated_titles(
    tmp_path: Path,
) -> None:
    memory_root = tmp_path / "memory"
    shutil.copytree(MEMORY_ROOT, memory_root)

    body = "# Lesson\n\n## Observation\n\n- Stable lesson\n\n## Reuse guidance\n\n- Reuse again later.\n"
    write_markdown_note(
        memory_root / "curated" / "lessons" / "duplicate-a.md",
        metadata={
            "id": "duplicate-a",
            "title": "Duplicate title",
            "kind": "lesson",
            "source_refs": ["src/memory/README.md"],
            "confidence": "curated",
            "last_verified": "2026-04-20T00:00:00Z",
            "summary": "First durable lesson for duplicate detection.",
        },
        body=body,
    )
    write_markdown_note(
        memory_root / "curated" / "lessons" / "duplicate-b.md",
        metadata={
            "id": "duplicate-b",
            "title": "Duplicate   title",
            "kind": "lesson",
            "source_refs": ["src/memory/DAILY_WORKFLOW.md"],
            "confidence": "curated",
            "last_verified": "2026-04-20T00:00:00Z",
            "summary": "Second durable lesson for duplicate detection.",
        },
        body=body,
    )

    issues = validate_memory_scaffold(memory_root)
    messages = {
        issue.message for issue in issues if issue.path.endswith("duplicate-b.md")
    }
    assert any(
        message.startswith("duplicate curated note title also used by ")
        for message in messages
    )


def test_memory_scaffold_validation_flags_invalid_storage_policy(
    tmp_path: Path,
) -> None:
    memory_root = tmp_path / "memory"
    shutil.copytree(MEMORY_ROOT, memory_root)

    (memory_root / "policy" / "storage.yaml").write_text(
        """version: 1
storage_modes: [versioned, rebuild_only, ephemeral]
artifact_classes:
  policy:
    storage_mode: versioned
    commit_to_git: true
    default_paths: ["policy"]
""",
        encoding="utf-8",
    )

    issues = validate_memory_scaffold(memory_root)
    messages = {
        issue.message for issue in issues if issue.path == "policy/storage.yaml"
    }
    assert "missing storage policy for artifact class: rag_manifest" in messages
    assert "default path for policy must stay under src/memory/: policy" in messages


def test_generated_memory_artifact_classifier_blocks_rebuild_only_outputs() -> None:
    assert _is_tracked_generated_memory_artifact(
        "src/memory/rag/manifests/chunks.jsonl"
    )
    assert _is_tracked_generated_memory_artifact(
        "src/memory/timeline/events/runs.jsonl"
    )
    assert _is_tracked_generated_memory_artifact(
        "src/memory/graph/projections/file_references.jsonl"
    )
    assert _is_tracked_generated_memory_artifact(
        "src/memory/graph/indexes/file_relations.json"
    )
    assert _is_tracked_generated_memory_artifact(
        "src/memory/__pycache__/query.cpython-312.pyc"
    )
    assert not _is_tracked_generated_memory_artifact(
        "src/memory/rag/manifests/README.md"
    )
    assert not _is_tracked_generated_memory_artifact("src/memory/README.md")


def test_memory_scaffold_validation_can_flag_working_tree_python_cache(
    tmp_path: Path,
) -> None:
    memory_root = tmp_path / "memory"
    shutil.copytree(MEMORY_ROOT, memory_root)
    cache_file = memory_root / "__pycache__" / "query.cpython-312.pyc"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(b"cache")

    issues = validate_memory_scaffold(memory_root, include_working_tree_junk=True)

    assert any(
        issue.path == str(cache_file)
        and issue.message
        == "working-tree Python cache should not live under src/memory"
        for issue in issues
    )


def test_memory_scaffold_validation_tolerates_root_init_bootstrap_cache(
    tmp_path: Path,
) -> None:
    memory_root = tmp_path / "memory"
    shutil.copytree(MEMORY_ROOT, memory_root)
    cache_file = memory_root / "__pycache__" / "__init__.cpython-313.pyc"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(b"cache")

    issues = validate_memory_scaffold(memory_root, include_working_tree_junk=True)

    assert not any(issue.path == str(cache_file) for issue in issues)


def test_validate_note_placement_does_not_resolve_paths(monkeypatch) -> None:
    memory_root = Path("/tmp/memory-root")
    note_path = memory_root / "curated" / "lessons" / "lesson.md"
    issues = []

    def _explode(self):  # pragma: no cover - regression guard
        raise AssertionError("resolve() should not be called for note placement")

    monkeypatch.setattr(Path, "resolve", _explode)

    _validate_note_placement(
        memory_root,
        note_path,
        "curated_note",
        {
            "rules": [
                {
                    "artifact_class": "curated_note",
                    "target_dir": "src/memory/curated/lessons",
                }
            ]
        },
        issues,
    )

    assert issues == []
