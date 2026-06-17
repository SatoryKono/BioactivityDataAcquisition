"""Unit tests for debt-governance gate helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from scripts.engineering.qa import report_debt_governance_gates as gates


def test_release_review_freshness_gate_passes_for_recent_live_review() -> None:
    gate = gates._release_review_freshness_gate(
        {"generated_at": "2026-06-04T15:01:29Z"},
        now=datetime(2026, 6, 17, 15, 1, 29, tzinfo=UTC),
    )

    assert gate.status == "pass"
    assert gate.name == "observability_release_review_freshness"
    assert gate.current == 13
    assert gate.limit == gates.RELEASE_REVIEW_MAX_AGE_DAYS


def test_release_review_freshness_gate_fails_for_stale_live_review() -> None:
    gate = gates._release_review_freshness_gate(
        {"generated_at": "2026-06-04T15:01:29Z"},
        now=datetime(2026, 7, 6, 15, 1, 29, tzinfo=UTC),
    )

    assert gate.status == "fail"
    assert gate.current == 32


def test_release_review_freshness_gate_fails_for_invalid_generated_at() -> None:
    gate = gates._release_review_freshness_gate(
        {"generated_at": "not-a-timestamp"},
        now=datetime(2026, 6, 17, tzinfo=UTC),
    )

    assert gate.status == "fail"
    assert gate.current == "missing_or_invalid"


def test_release_review_freshness_gate_fails_for_future_generated_at() -> None:
    gate = gates._release_review_freshness_gate(
        {"generated_at": "2026-06-18T00:00:00Z"},
        now=datetime(2026, 6, 17, 0, 0, 0, tzinfo=UTC),
    )

    assert gate.status == "fail"
    assert gate.current == -1
