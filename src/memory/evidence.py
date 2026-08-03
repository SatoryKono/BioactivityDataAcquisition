"""Immutable evidence and supersedable decision records."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from memory.records import RecordEnvelope, RecordType
from memory.security import (
    UnsafeMemoryContentError,
    assert_safe_for_persistence,
    inspect_memory_content,
)
from memory.storage import StorageConflictError, append_jsonl

_SHA256_HEX_LENGTH = 64


def _canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_digest(value: str, *, field: str) -> None:
    if len(value) != _SHA256_HEX_LENGTH:
        raise ValueError(f"{field} must be a SHA-256 digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{field} must be a SHA-256 digest") from exc


@dataclass(frozen=True, slots=True)
class EvidenceEvent:
    """One immutable, content-addressed evidence observation."""

    envelope: RecordEnvelope
    evidence_kind: str
    observation: str
    command: str | None = None
    result: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.envelope.record_type is not RecordType.EVIDENCE:
            raise ValueError("evidence envelope must use record_type=evidence")
        if not self.evidence_kind.strip():
            raise ValueError("evidence_kind must not be empty")
        if not self.observation.strip():
            raise ValueError("observation must not be empty")

    def content_payload(self) -> dict[str, Any]:
        """Return the digest-bearing content without a self-referential digest."""
        return {
            "envelope": self.envelope.to_dict(),
            "evidence_kind": self.evidence_kind,
            "observation": self.observation,
            "command": self.command,
            "result": self.result,
        }

    @property
    def evidence_digest(self) -> str:
        """Return the stable digest of envelope and evidence content."""
        return _canonical_digest(self.content_payload())

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical persistent representation."""
        return {
            **self.content_payload(),
            "evidence_digest": self.evidence_digest,
        }


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    """A decision that cites immutable evidence and uses supersession."""

    envelope: RecordEnvelope
    decision: str
    rationale: str
    evidence_digests: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.envelope.record_type is not RecordType.DECISION:
            raise ValueError("decision envelope must use record_type=decision")
        if not self.decision.strip():
            raise ValueError("decision must not be empty")
        if not self.rationale.strip():
            raise ValueError("rationale must not be empty")
        if not self.evidence_digests:
            raise ValueError("decision must cite at least one evidence digest")
        if len(self.evidence_digests) != len(set(self.evidence_digests)):
            raise ValueError("evidence_digests must be unique")
        for digest in self.evidence_digests:
            _validate_digest(digest, field="evidence_digest")

    def content_payload(self) -> dict[str, Any]:
        """Return the decision content used for its stable digest."""
        return {
            "envelope": self.envelope.to_dict(),
            "decision": self.decision,
            "rationale": self.rationale,
            "evidence_digests": list(self.evidence_digests),
        }

    @property
    def decision_digest(self) -> str:
        """Return the stable digest of the complete decision."""
        return _canonical_digest(self.content_payload())

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical persistent representation."""
        return {
            **self.content_payload(),
            "decision_digest": self.decision_digest,
        }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"JSONL record must be an object: {path}")
        records.append(payload)
    return records


class EvidenceStore:
    """Append-only evidence and decision logs under one caller-owned root."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._evidence_path = root / "evidence.jsonl"
        self._decision_path = root / "decisions.jsonl"

    def append_evidence(self, event: EvidenceEvent) -> str:
        """Append new evidence, rejecting duplicate identity or digest."""
        rendered = json.dumps(event.content_payload(), sort_keys=True)
        findings = inspect_memory_content(rendered)
        if findings:
            raise UnsafeMemoryContentError(findings)
        digest = event.evidence_digest
        record_id = event.envelope.record_id
        try:
            append_jsonl(
                self._evidence_path,
                event.to_dict(),
                reject_if=lambda row: (
                    row.get("evidence_digest") == digest
                    or row.get("envelope", {}).get("record_id") == record_id
                ),
                conflict_message="evidence record already exists",
            )
        except StorageConflictError as exc:
            raise ValueError("evidence record already exists") from exc
        return digest

    def append_decision(self, record: DecisionRecord) -> str:
        """Append a decision after resolving all cited evidence exactly."""
        assert_safe_for_persistence(
            f"{record.decision}\n{record.rationale}",
            trust=record.envelope.trust,
        )
        missing: list[str] = []
        scope_mismatches: list[str] = []
        for digest in record.evidence_digests:
            try:
                evidence = self.resolve_evidence(digest)
            except KeyError:
                missing.append(digest)
                continue
            evidence_envelope = evidence.get("envelope")
            if not isinstance(evidence_envelope, dict) or not _same_scope(
                evidence_envelope, record.envelope.to_dict()
            ):
                scope_mismatches.append(digest)
        if missing:
            raise ValueError(f"decision cites missing evidence: {', '.join(missing)}")
        if scope_mismatches:
            raise ValueError(
                "decision cites evidence outside its repository scope: "
                + ", ".join(scope_mismatches)
            )
        existing = _read_jsonl(self._decision_path)
        known_decision_ids = {
            str(row.get("envelope", {}).get("record_id")) for row in existing
        }
        record_id = record.envelope.record_id
        if record_id in known_decision_ids:
            raise ValueError("decision record already exists")
        missing_superseded = sorted(
            set(record.envelope.supersedes) - known_decision_ids
        )
        if missing_superseded:
            raise ValueError(
                f"decision supersedes unknown records: {', '.join(missing_superseded)}"
            )
        superseded_by_id = {
            str(row.get("envelope", {}).get("record_id")): row for row in existing
        }
        for superseded_id in record.envelope.supersedes:
            prior_envelope = superseded_by_id[superseded_id].get("envelope")
            if not isinstance(prior_envelope, dict) or not _same_scope(
                prior_envelope, record.envelope.to_dict()
            ):
                raise ValueError("decision supersedes a record outside its scope")
        try:
            append_jsonl(
                self._decision_path,
                record.to_dict(),
                reject_if=lambda row: (
                    row.get("envelope", {}).get("record_id") == record_id
                ),
                conflict_message="decision record already exists",
            )
        except StorageConflictError as exc:
            raise ValueError("decision record already exists") from exc
        return record.decision_digest

    def resolve_evidence(self, digest: str) -> dict[str, Any]:
        """Resolve one exact evidence digest, failing closed when absent."""
        _validate_digest(digest, field="evidence_digest")
        for row in _read_jsonl(self._evidence_path):
            if row.get("evidence_digest") == digest:
                content = {
                    key: value for key, value in row.items() if key != "evidence_digest"
                }
                if _canonical_digest(content) != digest:
                    raise ValueError("evidence digest mismatch")
                return row
        raise KeyError(digest)


_SCOPE_FIELDS = ("repo_id", "git_commit", "branch", "worktree_id", "task_id")


def _same_scope(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Require exact repository-version-task compatibility."""
    return all(left.get(field) == right.get(field) for field in _SCOPE_FIELDS)
