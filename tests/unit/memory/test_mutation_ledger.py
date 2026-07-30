"""Mutation audit ledger contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.ledger import MutationEvent, MutationLedger
from memory.records import ActorIdentity

pytestmark = pytest.mark.unit


def _event(event_id: str, operation: str = "create") -> MutationEvent:
    return MutationEvent(
        event_id=event_id,
        operation=operation,
        record_id="record-1",
        repo_id="bioetl",
        git_commit="a" * 40,
        branch="main",
        worktree_id="tree",
        task_id="task",
        actor=ActorIdentity(runtime="codex", agent="primary", model="test-model"),
        occurred_at="2026-07-29T00:00:00+00:00",
        reason="verified update",
        previous_digest="b" * 64 if operation != "create" else None,
        new_digest=None if operation == "delete" else "c" * 64,
    )


def test_ledger_is_attributable_content_free_and_bounded(tmp_path: Path) -> None:
    ledger = MutationLedger(tmp_path / "audit.jsonl")
    digest = ledger.append(_event("event-1"))

    history = ledger.history("record-1", limit=1)

    assert history[0]["event_digest"] == digest
    assert history[0]["actor"]["runtime"] == "codex"
    assert "content" not in history[0]


def test_ledger_rejects_duplicate_and_detects_tamper(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    ledger = MutationLedger(path)
    ledger.append(_event("event-1"))
    with pytest.raises(ValueError, match="already exists"):
        ledger.append(_event("event-1"))
    path.write_text(path.read_text().replace("verified", "altered"), encoding="utf-8")
    with pytest.raises(ValueError, match="digest mismatch"):
        ledger.history("record-1")
