"""Tests for immutable evidence and supersedable decision logs."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.evidence import DecisionRecord, EvidenceEvent, EvidenceStore
from memory.records import (
    ActorIdentity,
    RecordEnvelope,
    RecordScope,
    RecordType,
    TrustLevel,
)

pytestmark = pytest.mark.unit
_COMMIT = "a" * 40


def _envelope(
    record_id: str,
    record_type: RecordType,
    *,
    supersedes: tuple[str, ...] = (),
    repo_id: str = "bioetl",
) -> RecordEnvelope:
    return RecordEnvelope.create(
        record_id=record_id,
        record_type=record_type,
        scope=RecordScope(repo_id, _COMMIT, "main", "worktree-a", "issue-7187"),
        actor=ActorIdentity(runtime="codex", agent="test", model=None),
        source_refs=("src/memory/README.md",),
        trust=TrustLevel.TRUSTED_REPOSITORY,
        supersedes=supersedes,
        created_at="2026-07-29T00:00:00+00:00",
    )


def test_evidence_is_append_only_and_digest_detects_mutation(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path)
    event = EvidenceEvent(
        envelope=_envelope("evidence-1", RecordType.EVIDENCE),
        evidence_kind="command-result",
        observation="Targeted tests passed.",
        command="pytest tests/unit/memory -q",
        result={"exit_code": 0},
    )

    digest = store.append_evidence(event)
    assert store.resolve_evidence(digest)["observation"] == "Targeted tests passed."
    with pytest.raises(ValueError, match="already exists"):
        store.append_evidence(event)

    evidence_path = tmp_path / "evidence.jsonl"
    evidence_path.write_text(
        evidence_path.read_text(encoding="utf-8").replace("passed", "failed"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="digest mismatch"):
        store.resolve_evidence(digest)


def test_decision_requires_resolvable_evidence_and_known_supersession(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path)
    unresolved = DecisionRecord(
        envelope=_envelope("decision-missing", RecordType.DECISION),
        decision="Do not accept missing evidence.",
        rationale="Decision replay must fail closed.",
        evidence_digests=("f" * 64,),
    )
    with pytest.raises(ValueError, match="cites missing evidence"):
        store.append_decision(unresolved)

    evidence = EvidenceEvent(
        envelope=_envelope("evidence-1", RecordType.EVIDENCE),
        evidence_kind="repository-fact",
        observation="The registry validates.",
    )
    evidence_digest = store.append_evidence(evidence)
    first = DecisionRecord(
        envelope=_envelope("decision-1", RecordType.DECISION),
        decision="Adopt the registry.",
        rationale="The repository evidence is complete.",
        evidence_digests=(evidence_digest,),
    )
    assert len(store.append_decision(first)) == 64

    replacement = DecisionRecord(
        envelope=_envelope(
            "decision-2",
            RecordType.DECISION,
            supersedes=("decision-1",),
        ),
        decision="Adopt the revised registry.",
        rationale="New evidence supersedes the earlier scope.",
        evidence_digests=(evidence_digest,),
    )
    assert len(store.append_decision(replacement)) == 64

    unknown = DecisionRecord(
        envelope=_envelope(
            "decision-3",
            RecordType.DECISION,
            supersedes=("missing-decision",),
        ),
        decision="Invalid supersession.",
        rationale="This must fail closed.",
        evidence_digests=(evidence_digest,),
    )
    with pytest.raises(ValueError, match="supersedes unknown"):
        store.append_decision(unknown)


def test_decision_rejects_evidence_from_another_repository(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path)
    evidence = EvidenceEvent(
        envelope=_envelope(
            "foreign-evidence", RecordType.EVIDENCE, repo_id="other-repository"
        ),
        evidence_kind="repository-fact",
        observation="This observation belongs to another repository.",
    )
    digest = store.append_evidence(evidence)
    decision = DecisionRecord(
        envelope=_envelope("decision-local", RecordType.DECISION),
        decision="Do not cross repository boundaries.",
        rationale="Repository evidence must remain isolated.",
        evidence_digests=(digest,),
    )

    with pytest.raises(ValueError, match="outside its repository scope"):
        store.append_decision(decision)
