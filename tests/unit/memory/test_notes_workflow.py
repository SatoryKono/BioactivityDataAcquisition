"""Tests for markdown note templates and promotion workflow."""

from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import memory.notes as notes_module
import memory.tooling.promote_note as promote_note_module
from memory.notes import parse_markdown_note
from memory.tooling.archive_note import archive_note
from memory.tooling.create_note import create_note
from memory.tooling.promote_note import promote_note


def test_create_episodic_session_note(tmp_path: Path) -> None:
    path = create_note(
        note_kind="episodic-session",
        title="Memory rollout task",
        task_id="task-123",
        source_refs=[
            "docs/plans/project-memory-layer-implementation-plan-2026-04-20.md"
        ],
        output_path=tmp_path / "session.md",
    )
    assert path.exists()
    note = parse_markdown_note(path)
    assert note.metadata["task_id"] == "task-123"
    assert note.metadata["ttl_days"] == 14
    assert note.metadata["confidence"] == "episodic"
    assert "## Current context" in note.body


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
    assert "## Observation" in note.body
    assert "## Reuse guidance" in note.body


def test_parse_markdown_note_can_skip_body_loading(tmp_path: Path) -> None:
    path = create_note(
        note_kind="episodic-session",
        title="Skip body",
        task_id="task-skip",
        source_refs=["src/memory/README.md"],
        output_path=tmp_path / "session.md",
    )

    note = parse_markdown_note(path, include_body=False)

    assert note.metadata["task_id"] == "task-skip"
    assert note.body == ""


def test_parse_markdown_note_metadata_only_preserves_quoted_numeric_strings(
    tmp_path: Path,
) -> None:
    path = tmp_path / "quoted.md"
    path.write_text(
        "---\n"
        "id: '3467'\n"
        'task_id: "3507"\n'
        "created_at: '2026-04-20T00:00:00Z'\n"
        "ttl_days: 14\n"
        "confidence: episodic\n"
        "source_refs:\n"
        "- src/memory/README.md\n"
        "---\n\n"
        "# Session\n",
        encoding="utf-8",
    )

    note = parse_markdown_note(path, include_body=False)

    assert note.metadata["id"] == "3467"
    assert note.metadata["task_id"] == "3507"
    assert note.metadata["ttl_days"] == 14


def test_hidden_windows_subprocess_kwargs_prevent_console_popups() -> None:
    startupinfo = SimpleNamespace(dwFlags=0, wShowWindow=5)
    fake_subprocess = SimpleNamespace(
        CREATE_NO_WINDOW=0x08000000,
        STARTF_USESHOWWINDOW=0x00000001,
        SW_HIDE=0,
        STARTUPINFO=lambda: startupinfo,
    )

    kwargs = notes_module._hidden_windows_subprocess_kwargs(
        os_name="nt",
        subprocess_module=fake_subprocess,
    )

    assert kwargs["creationflags"] == 0x08000000
    assert kwargs["startupinfo"] is startupinfo
    assert startupinfo.dwFlags == 0x00000001
    assert startupinfo.wShowWindow == 0


def test_git_repo_root_uses_packaged_root_for_repo_memory_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(notes_module.__file__).parents[2]
    note_path = repo_root / "src" / "memory" / "episodic" / "sessions" / "3552.md"

    def unexpected_subprocess_run(*args: object, **kwargs: object) -> object:
        _ = (args, kwargs)
        raise AssertionError("packaged memory path should not shell out to rev-parse")

    monkeypatch.setattr(notes_module.subprocess, "run", unexpected_subprocess_run)

    assert notes_module._git_repo_root(note_path) == repo_root


def test_parse_markdown_note_timeout_does_not_wait_for_blocked_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "blocked.md"
    path.write_text("---\nid: blocked\n---\n", encoding="utf-8")

    def blocked_read_text(self: Path, *, encoding: str | None = None) -> str:
        _ = (self, encoding)
        time.sleep(1.0)
        return ""

    monkeypatch.setattr(notes_module, "NOTE_READ_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(notes_module, "_read_text_from_git_object", lambda _: None)
    monkeypatch.setattr(notes_module, "_is_likely_network_drive", lambda _: True)
    monkeypatch.setattr(Path, "read_text", blocked_read_text)

    started_at = time.monotonic()
    with pytest.raises(ValueError, match="failed to open note file"):
        parse_markdown_note(path)

    assert time.monotonic() - started_at < 0.5


def test_parse_markdown_note_uses_git_fallback_when_worktree_read_times_out(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "tracked.md"
    path.write_text("---\nid: tracked\n---\n", encoding="utf-8")

    read_started = threading.Event()
    read_should_complete = threading.Event()

    def blocked_read_text(self: Path, *, encoding: str | None = None) -> str:
        _ = (self, encoding)
        read_started.set()
        read_should_complete.wait(timeout=10.0)
        return ""

    monkeypatch.setattr(notes_module, "NOTE_READ_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(notes_module, "_is_likely_network_drive", lambda _: True)
    monkeypatch.setattr(
        notes_module,
        "_read_text_from_git_object",
        lambda _: (
            "---\n"
            "id: tracked\n"
            "task_id: task-123\n"
            "created_at: '2026-05-26T00:00:00Z'\n"
            "ttl_days: 14\n"
            "confidence: episodic\n"
            "source_refs:\n"
            "- src/memory/README.md\n"
            "---\n\n"
            "# Session\n"
        ),
    )
    monkeypatch.setattr(Path, "read_text", blocked_read_text)

    note = parse_markdown_note(path, include_body=False)

    read_should_complete.set()

    assert note.metadata["id"] == "tracked"
    assert note.metadata["task_id"] == "task-123"


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
        summary="Reusable lesson for future memory tasks.",
        output_path=tmp_path / "curated.md",
        move=True,
    )

    assert not source.exists()
    note = parse_markdown_note(output)
    assert note.metadata["kind"] == "lesson"
    assert note.metadata["confidence"] == "curated"
    assert note.metadata["promoted_from"].endswith("episodic.md")
    assert "task_id" not in note.metadata
    assert note.metadata["summary"] == "Reusable lesson for future memory tasks."
    assert "## Observation" in note.body


def test_promote_note_rejects_duplicate_curated_note_without_override(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = create_note(
        note_kind="episodic-summary",
        title="Duplicate me",
        task_id="task-dup",
        source_refs=["src/memory/README.md"],
        output_path=tmp_path / "episodic.md",
    )
    existing = tmp_path / "curated-existing.md"
    create_note(
        note_kind="curated-lesson",
        title="Duplicate me",
        task_id=None,
        source_refs=["src/memory/README.md"],
        output_path=existing,
    )
    monkeypatch.setattr(
        promote_note_module,
        "_existing_curated_notes",
        lambda exclude=None: [existing],
    )

    try:
        promote_note(
            source,
            target_kind="lesson",
            summary="Duplicate summary that should be blocked.",
            output_path=tmp_path / "duplicate-target.md",
        )
    except ValueError as exc:
        assert "duplicate curated note detected" in str(exc)
    else:
        raise AssertionError("expected duplicate promotion to be rejected")


def test_archive_note_moves_curated_note_into_archive(tmp_path: Path) -> None:
    source = create_note(
        note_kind="curated-lesson",
        title="Archive me",
        task_id=None,
        source_refs=["src/memory/README.md"],
        output_path=tmp_path / "lesson.md",
    )
    archived = archive_note(
        source,
        reason="Superseded by newer guidance.",
        output_path=tmp_path / "archive" / "lesson.md",
        move=True,
    )
    assert not source.exists()
    note = parse_markdown_note(archived)
    assert note.metadata["archived_reason"] == "Superseded by newer guidance."
    assert note.metadata["archived_from"].endswith("lesson.md")
