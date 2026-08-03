"""Tests for the memory lifecycle state machine."""

from __future__ import annotations

import pytest

from memory.lifecycle import IllegalTransitionError, can_transition, transition
from memory.records import RecordStatus

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("previous", "current"),
    [
        (RecordStatus.ACTIVE, RecordStatus.STALE),
        (RecordStatus.ACTIVE, RecordStatus.SUPERSEDED),
        (RecordStatus.ACTIVE, RecordStatus.ARCHIVED),
        (RecordStatus.STALE, RecordStatus.ACTIVE),
        (RecordStatus.STALE, RecordStatus.SUPERSEDED),
        (RecordStatus.SUPERSEDED, RecordStatus.ARCHIVED),
    ],
)
def test_legal_transitions(previous: RecordStatus, current: RecordStatus) -> None:
    assert can_transition(previous, current)


@pytest.mark.parametrize(
    ("previous", "current"),
    [
        (RecordStatus.ACTIVE, RecordStatus.ACTIVE),
        (RecordStatus.SUPERSEDED, RecordStatus.ACTIVE),
        (RecordStatus.ARCHIVED, RecordStatus.ACTIVE),
        (RecordStatus.ARCHIVED, RecordStatus.STALE),
    ],
)
def test_illegal_transitions_are_rejected(
    previous: RecordStatus,
    current: RecordStatus,
) -> None:
    with pytest.raises(IllegalTransitionError, match="illegal memory lifecycle"):
        transition(
            record_id="record-1",
            previous=previous,
            current=current,
            reason="test",
            actor="codex",
        )


def test_transition_requires_auditable_reason_and_actor() -> None:
    with pytest.raises(IllegalTransitionError, match="reason"):
        transition(
            record_id="record-1",
            previous=RecordStatus.ACTIVE,
            current=RecordStatus.STALE,
            reason=" ",
            actor="codex",
        )


def test_transition_preserves_explicit_timestamp() -> None:
    event = transition(
        record_id="record-1",
        previous=RecordStatus.ACTIVE,
        current=RecordStatus.STALE,
        reason="source changed",
        actor="codex",
        occurred_at="2026-07-29T12:00:00+00:00",
    )

    assert event.occurred_at == "2026-07-29T12:00:00+00:00"
