"""Tests for curated memory review loop tooling."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from memory.notes import write_markdown_note
from memory.tooling.review_curated import review_curated_notes


def _lesson_body() -> str:
    return (
        "# Lesson\n\n"
        "## Observation\n\n"
        "- Durable lesson\n\n"
        "## Reuse guidance\n\n"
        "- Apply when the same conditions return.\n"
    )


def test_review_curated_notes_marks_due_and_stale_records(tmp_path: Path) -> None:
    curated_root = tmp_path / "curated"
    (curated_root / "lessons").mkdir(parents=True)
    (curated_root / "archive").mkdir(parents=True)

    write_markdown_note(
        curated_root / "lessons" / "current.md",
        metadata={
            "id": "current",
            "title": "Current lesson",
            "kind": "lesson",
            "source_refs": ["src/memory/README.md", "src/memory/DAILY_WORKFLOW.md"],
            "confidence": "curated",
            "last_verified": "2026-04-15T00:00:00Z",
            "summary": "Current durable lesson for future tasks.",
        },
        body=_lesson_body(),
    )
    write_markdown_note(
        curated_root / "lessons" / "due.md",
        metadata={
            "id": "due",
            "title": "Due lesson",
            "kind": "lesson",
            "source_refs": ["src/memory/README.md", "src/memory/DAILY_WORKFLOW.md"],
            "confidence": "curated",
            "last_verified": "2025-12-01T00:00:00Z",
            "summary": "Due durable lesson for future tasks.",
        },
        body=_lesson_body(),
    )
    write_markdown_note(
        curated_root / "lessons" / "stale.md",
        metadata={
            "id": "stale",
            "title": "Stale lesson",
            "kind": "lesson",
            "source_refs": ["src/memory/README.md"],
            "confidence": "curated",
            "last_verified": "2025-08-01T00:00:00Z",
            "summary": "Stale durable lesson for future tasks.",
        },
        body=_lesson_body(),
    )
    write_markdown_note(
        curated_root / "lessons" / "thin-current.md",
        metadata={
            "id": "thin-current",
            "title": "Thin current lesson",
            "kind": "lesson",
            "source_refs": ["src/memory/README.md"],
            "confidence": "curated",
            "last_verified": "2026-04-15T00:00:00Z",
            "summary": "Current lesson with thin provenance.",
        },
        body=_lesson_body(),
    )

    report = review_curated_notes(
        curated_root,
        now=datetime(2026, 4, 20, tzinfo=UTC),
    )
    records = {record["note_id"]: record for record in report["records"]}

    assert records["current"]["review_status"] == "current"
    assert records["current"]["recommendation"] == "keep"
    assert records["due"]["review_status"] == "due"
    assert records["due"]["recommendation"] == "review"
    assert records["stale"]["review_status"] == "stale"
    assert records["stale"]["recommendation"] == "review_or_archive"
    assert "source_refs:thin" in records["stale"]["review_reasons"]
    assert records["thin-current"]["review_status"] == "current"
    assert records["thin-current"]["recommendation"] == "review"
    assert "source_refs:thin" in records["thin-current"]["review_reasons"]


def test_review_curated_notes_flags_duplicate_titles(tmp_path: Path) -> None:
    curated_root = tmp_path / "curated"
    (curated_root / "lessons").mkdir(parents=True)

    write_markdown_note(
        curated_root / "lessons" / "one.md",
        metadata={
            "id": "one",
            "title": "Shared title",
            "kind": "lesson",
            "source_refs": ["src/memory/README.md", "src/memory/DAILY_WORKFLOW.md"],
            "confidence": "curated",
            "last_verified": "2026-04-20T00:00:00Z",
            "summary": "First durable lesson for duplicate review.",
        },
        body=_lesson_body(),
    )
    write_markdown_note(
        curated_root / "lessons" / "two.md",
        metadata={
            "id": "two",
            "title": "Shared   title",
            "kind": "lesson",
            "source_refs": ["src/memory/query.py", "src/memory/README.md"],
            "confidence": "curated",
            "last_verified": "2026-04-20T00:00:00Z",
            "summary": "Second durable lesson for duplicate review.",
        },
        body=_lesson_body(),
    )

    report = review_curated_notes(
        curated_root,
        now=datetime(2026, 4, 20, tzinfo=UTC),
    )
    records = {record["note_id"]: record for record in report["records"]}
    assert "duplicate:title" in records["one"]["review_reasons"]
    assert "duplicate:title" in records["two"]["review_reasons"]
    assert records["one"]["recommendation"] == "review"
    assert records["two"]["recommendation"] == "review"
