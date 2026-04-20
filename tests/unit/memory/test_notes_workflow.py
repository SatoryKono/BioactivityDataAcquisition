"""Tests for markdown note templates and promotion workflow."""

from __future__ import annotations

from pathlib import Path

from memory.notes import parse_markdown_note
from memory.tooling.create_note import create_note
from memory.tooling.promote_note import promote_note


def test_create_episodic_session_note(tmp_path: Path) -> None:
    path = create_note(
        note_kind="episodic-session",
        title="Memory rollout task",
        task_id="task-123",
        source_refs=["docs/plans/project-memory-layer-implementation-plan-2026-04-20.md"],
        output_path=tmp_path / "session.md",
    )
    assert path.exists()
    note = parse_markdown_note(path)
    assert note.metadata["task_id"] == "task-123"
    assert note.metadata["ttl_days"] == 14
    assert "Context" in note.body


def test_create_curated_lesson_note(tmp_path: Path) -> None:
    path = create_note(
        note_kind="curated-lesson",
        title="Memory lesson",
        task_id=None,
        source_refs=["src/memory/README.md"],
        output_path=tmp_path / "lesson.md",
    )
    note = parse_markdown_note(path)
    assert note.metadata["kind"] == "lesson"
    assert note.metadata["confidence"] == "curated"


def test_promote_note_moves_episodic_into_curated(tmp_path: Path) -> None:
    source = create_note(
        note_kind="episodic-summary",
        title="Promote me",
        task_id="task-456",
        source_refs=["src/memory/README.md"],
        output_path=tmp_path / "episodic.md",
    )
    output = promote_note(
        source,
        target_kind="lesson",
        output_path=tmp_path / "curated.md",
        move=True,
    )

    assert not source.exists()
    note = parse_markdown_note(output)
    assert note.metadata["kind"] == "lesson"
    assert note.metadata["confidence"] == "curated"
    assert note.metadata["promoted_from"].endswith("episodic.md")
    assert "task_id" not in note.metadata
