"""End-to-end replay from immutable evidence without hidden session state."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.evidence import DecisionRecord, EvidenceEvent, EvidenceStore
from memory.records import ActorIdentity, RecordEnvelope, RecordType, TrustLevel
from memory.replay import replay_decision

pytestmark = pytest.mark.integration


def _envelope(record_id: str, record_type: RecordType) -> RecordEnvelope:
    return RecordEnvelope.create(
        record_id=record_id,
        record_type=record_type,
        repo_id="bioetl",
        git_commit="a" * 40,
        branch="main",
        worktree_id="tree-a",
        task_id="task-replay",
        actor=ActorIdentity(runtime="test", agent="replay"),
        source_refs=("docs/00-project/RULES.md",),
        trust=TrustLevel.TRUSTED_REPOSITORY,
        created_at="2026-07-29T00:00:00+00:00",
    )


def test_decision_replay_resolves_identical_evidence_and_constraints(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path)
    event = EvidenceEvent(
        envelope=_envelope("evidence-1", RecordType.EVIDENCE),
        evidence_kind="test-result",
        observation="The deterministic contract passed.",
        command="pytest test_contract.py",
        result={"exit_code": 0},
    )
    evidence_digest = store.append_evidence(event)
    decision = DecisionRecord(
        envelope=_envelope("decision-1", RecordType.DECISION),
        decision="Adopt the contract.",
        rationale="The cited repository test passed.",
        evidence_digests=(evidence_digest,),
    )
    decision_digest = store.append_decision(decision)

    first = replay_decision(tmp_path, decision_digest)
    second = replay_decision(tmp_path, decision_digest)

    assert first == second
    assert first.evidence_digests == (evidence_digest,)
    assert first.repository_commit == "a" * 40
    assert first.to_dict()["model_step"] == "excluded"


def test_decision_replay_fails_closed_when_evidence_is_missing(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path)
    event = EvidenceEvent(
        envelope=_envelope("evidence-1", RecordType.EVIDENCE),
        evidence_kind="test-result",
        observation="Observed.",
    )
    evidence_digest = store.append_evidence(event)
    decision = DecisionRecord(
        envelope=_envelope("decision-1", RecordType.DECISION),
        decision="Use evidence.",
        rationale="Evidence is mandatory.",
        evidence_digests=(evidence_digest,),
    )
    decision_digest = store.append_decision(decision)
    (tmp_path / "evidence.jsonl").unlink()

    with pytest.raises(KeyError):
        replay_decision(tmp_path, decision_digest)
