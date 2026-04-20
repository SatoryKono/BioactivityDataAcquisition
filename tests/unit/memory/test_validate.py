"""Tests for the baseline project-memory scaffold validator."""

from __future__ import annotations

import shutil
from pathlib import Path

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
from memory.validation import validate_memory_scaffold


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
            "summary": "Durable lesson.",
        },
        body="# Lesson\n\n- Durable guidance\n",
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


def test_memory_scaffold_validation_flags_invalid_note_files(tmp_path: Path) -> None:
    memory_root = tmp_path / "memory"
    shutil.copytree(MEMORY_ROOT, memory_root)

    write_markdown_note(
        memory_root / "curated" / "lessons" / "broken-lesson.md",
        metadata={
            "id": "broken-lesson",
            "title": "Broken lesson",
            "kind": "lesson",
            "source_refs": [],
            "confidence": "episodic",
            "summary": "Missing verification and wrong confidence.",
        },
        body="# Broken\n",
    )

    issues = validate_memory_scaffold(memory_root)
    messages = {issue.message for issue in issues if issue.path.endswith("broken-lesson.md")}
    assert "note missing required field: last_verified" in messages
    assert "note source_refs must be a non-empty list" in messages
    assert "note confidence must be 'curated' for curated_note" in messages


def test_memory_scaffold_validation_flags_invalid_storage_policy(tmp_path: Path) -> None:
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
    messages = {issue.message for issue in issues if issue.path == "policy/storage.yaml"}
    assert "missing storage policy for artifact class: rag_manifest" in messages
    assert (
        "default path for policy must stay under src/memory/: policy"
        in messages
    )
