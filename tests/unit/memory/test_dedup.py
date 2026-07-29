"""Tests for deterministic semantic memory deduplication."""

from __future__ import annotations

from memory.dedup import (
    DedupCandidate,
    DuplicateKind,
    build_dedup_report,
    semantic_key,
)


def _candidate(
    record_id: str,
    title: str,
    digest: str,
    *source_refs: str,
) -> DedupCandidate:
    return DedupCandidate(
        record_id=record_id,
        record_type="lesson",
        title=title,
        content_digest=digest,
        source_refs=source_refs,
    )


def test_semantic_key_normalizes_case_unicode_and_whitespace() -> None:
    first = semantic_key(record_type="Lesson", title="Atomic   Writes")
    second = semantic_key(record_type="lesson", title=" atomic writes ")

    assert first == second
    assert len(first) == 64


def test_exact_duplicates_have_one_digest() -> None:
    report = build_dedup_report(
        (
            _candidate("b", "Atomic writes", "a" * 64, "source-b"),
            _candidate("a", "atomic  writes", "a" * 64, "source-a"),
        )
    )

    assert report.candidate_count == 2
    assert report.unique_key_count == 1
    assert report.conflicts[0].kind is DuplicateKind.EXACT
    assert report.conflicts[0].record_ids == ("a", "b")
    assert report.conflicts[0].source_refs == ("source-a", "source-b")


def test_conflicting_duplicates_preserve_all_provenance() -> None:
    report = build_dedup_report(
        (
            _candidate("a", "Retention policy", "a" * 64, "policy-a"),
            _candidate("b", "retention policy", "b" * 64, "policy-b"),
        )
    )

    conflict = report.conflicts[0]
    assert conflict.kind is DuplicateKind.CONFLICTING
    assert conflict.content_digests == ("a" * 64, "b" * 64)
    assert conflict.source_refs == ("policy-a", "policy-b")


def test_report_is_independent_of_input_order() -> None:
    candidates = (
        _candidate("a", "One", "a" * 64),
        _candidate("b", "one", "b" * 64),
        _candidate("c", "Two", "c" * 64),
        _candidate("d", "two", "c" * 64),
    )

    assert build_dedup_report(candidates) == build_dedup_report(
        tuple(reversed(candidates))
    )


def test_unique_candidates_do_not_create_conflicts() -> None:
    report = build_dedup_report(
        (
            _candidate("a", "One", "a" * 64),
            _candidate("b", "Two", "b" * 64),
        )
    )

    assert report.unique_key_count == 2
    assert report.conflict_count == 0
