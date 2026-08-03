"""Tests for the vendor-neutral memory record envelope."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from memory.records import ActorIdentity, RecordEnvelope, RecordType, TrustLevel

pytestmark = pytest.mark.unit


def _envelope() -> RecordEnvelope:
    return RecordEnvelope.create(
        record_id="record-1",
        record_type=RecordType.EVIDENCE,
        repo_id="bioactivitydataacquisition",
        git_commit="a" * 40,
        branch="main",
        worktree_id="worktree-1",
        task_id="task-1",
        actor=ActorIdentity(runtime="codex", agent="py-plan-bot", model=None),
        source_refs=("src/memory/README.md",),
        source_hashes={"src/memory/README.md": "b" * 64},
        trust=TrustLevel.TRUSTED_REPOSITORY,
        created_at="2026-07-29T12:00:00+00:00",
    )


def test_record_envelope_is_schema_valid() -> None:
    schema_path = (
        Path(__file__).parents[3]
        / "src"
        / "memory"
        / "schemas"
        / "record_envelope.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert (
        jsonschema.Draft202012Validator(schema).validate(_envelope().to_dict()) is None
    )


def test_record_envelope_digest_is_deterministic() -> None:
    first = _envelope()
    second = _envelope()

    assert first.content_digest == second.content_digest
    assert len(first.content_digest) == 64


def test_record_envelope_digest_changes_with_provenance() -> None:
    original = _envelope()
    changed = RecordEnvelope.create(
        record_id=original.record_id,
        record_type=original.record_type,
        repo_id=original.repo_id,
        git_commit="c" * 40,
        branch=original.branch,
        worktree_id=original.worktree_id,
        task_id=original.task_id,
        actor=original.actor,
        source_refs=original.source_refs,
        source_hashes=original.source_hashes,
        trust=original.trust,
        created_at=original.created_at,
    )

    assert changed.content_digest != original.content_digest
