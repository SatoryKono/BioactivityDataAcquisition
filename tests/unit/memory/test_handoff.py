"""Tests for bounded, allowlisted subagent handoffs."""

from __future__ import annotations

import json

import pytest

from memory.handoff import HandoffRecord
from memory.records import ActorIdentity, RecordEnvelope, RecordScope, RecordType

pytestmark = pytest.mark.unit


def _envelope() -> RecordEnvelope:
    return RecordEnvelope.create(
        record_id="handoff-1",
        record_type=RecordType.WORKING,
        scope=RecordScope("bioetl", "b" * 40, "main", "worktree-a", "issue-7190"),
        actor=ActorIdentity(runtime="codex", agent="orchestrator", model=None),
        source_refs=("src/memory/evidence.py",),
        created_at="2026-07-29T00:00:00+00:00",
    )


def test_handoff_is_deterministic_bounded_and_allowlisted() -> None:
    digest = "c" * 64
    handoff = HandoffRecord(
        envelope=_envelope(),
        objective="Review the evidence-store implementation.",
        constraints=("read-only review", "cite file lines"),
        evidence_digests=(digest,),
        context={
            "findings": ["Check append-only semantics."],
            "files": ["src/memory/evidence.py"],
        },
    )

    first = handoff.to_bounded_json()
    second = handoff.to_bounded_json()

    assert first == second
    payload = json.loads(first)
    assert set(payload) == {
        "schema_version",
        "envelope",
        "objective",
        "constraints",
        "evidence_digests",
        "context",
    }
    assert "conversation" not in first


def test_handoff_rejects_forbidden_context_and_oversized_payload() -> None:
    with pytest.raises(ValueError, match="forbidden fields"):
        HandoffRecord(
            envelope=_envelope(),
            objective="Unsafe handoff.",
            constraints=("bounded",),
            evidence_digests=(),
            context={"conversation": ["full private session"]},
        )

    handoff = HandoffRecord(
        envelope=_envelope(),
        objective="Bounded handoff.",
        constraints=("bounded",),
        evidence_digests=(),
        context={"findings": ["x" * 100]},
    )
    with pytest.raises(ValueError, match="byte budget"):
        handoff.to_bounded_json(max_bytes=64)
