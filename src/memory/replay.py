"""Deterministic replay of evidence-bound repository decisions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from memory.evidence import EvidenceStore, _same_scope


def _digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class ReplayResult:
    """Evidence and constraints resolved without invoking a model."""

    decision_digest: str
    decision: str
    rationale: str
    evidence_digests: tuple[str, ...]
    repository_commit: str
    task_id: str
    deterministic: bool = True

    def to_dict(self) -> dict[str, object]:
        """Return the stable machine-readable replay result."""
        return {
            "decision_digest": self.decision_digest,
            "decision": self.decision,
            "rationale": self.rationale,
            "evidence_digests": list(self.evidence_digests),
            "repository_commit": self.repository_commit,
            "task_id": self.task_id,
            "deterministic": self.deterministic,
            "model_step": "excluded",
        }


def replay_decision(root: Path, decision_digest: str) -> ReplayResult:
    """Resolve a decision and every cited evidence digest, failing closed."""
    decision_path = root / "decisions.jsonl"
    if not decision_path.exists():
        raise KeyError(decision_digest)
    matched: dict[str, Any] | None = None
    for line in decision_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, dict) and row.get("decision_digest") == decision_digest:
            matched = row
            break
    if matched is None:
        raise KeyError(decision_digest)
    content = {key: value for key, value in matched.items() if key != "decision_digest"}
    if _digest(content) != decision_digest:
        raise ValueError("decision digest mismatch")

    raw_digests = matched.get("evidence_digests")
    if not isinstance(raw_digests, list) or not raw_digests:
        raise ValueError("decision has no replayable evidence")
    evidence_digests = tuple(str(value) for value in raw_digests)
    envelope = matched.get("envelope")
    if not isinstance(envelope, dict):
        raise ValueError("decision envelope is missing")
    store = EvidenceStore(root)
    for evidence_digest in evidence_digests:
        evidence = store.resolve_evidence(evidence_digest)
        evidence_envelope = evidence.get("envelope")
        if not isinstance(evidence_envelope, dict) or not _same_scope(
            evidence_envelope, envelope
        ):
            raise ValueError("decision evidence scope mismatch")
    return ReplayResult(
        decision_digest=decision_digest,
        decision=str(matched.get("decision") or ""),
        rationale=str(matched.get("rationale") or ""),
        evidence_digests=evidence_digests,
        repository_commit=str(envelope.get("git_commit") or ""),
        task_id=str(envelope.get("task_id") or ""),
    )
