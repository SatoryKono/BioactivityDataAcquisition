"""Bounded, allowlisted subagent handoff records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from memory.records import RecordEnvelope, RecordType

DEFAULT_MAX_HANDOFF_BYTES = 16_384
ALLOWED_CONTEXT_FIELDS = frozenset({"files", "symbols", "commands", "findings"})
_SHA256_HEX_LENGTH = 64


def _validate_evidence_digest(value: str) -> None:
    if len(value) != _SHA256_HEX_LENGTH:
        raise ValueError("evidence digest must be a SHA-256 digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError("evidence digest must be a SHA-256 digest") from exc


def _validate_string_sequence(value: object, *, field: str) -> None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError(f"context.{field} must be a list of non-empty strings")


@dataclass(frozen=True, slots=True)
class HandoffRecord:
    """A task-scoped handoff with no conversation or user-memory fields."""

    envelope: RecordEnvelope
    objective: str
    constraints: tuple[str, ...]
    evidence_digests: tuple[str, ...]
    context: dict[str, list[str]]

    def __post_init__(self) -> None:
        if self.envelope.record_type is not RecordType.WORKING:
            raise ValueError("handoff envelope must use record_type=working")
        if not self.objective.strip():
            raise ValueError("objective must not be empty")
        if not self.constraints:
            raise ValueError("handoff must declare at least one constraint")
        if not all(item.strip() for item in self.constraints):
            raise ValueError("constraints must not contain empty values")
        if len(self.constraints) != len(set(self.constraints)):
            raise ValueError("constraints must be unique")
        if len(self.evidence_digests) != len(set(self.evidence_digests)):
            raise ValueError("evidence_digests must be unique")
        for digest in self.evidence_digests:
            _validate_evidence_digest(digest)
        unexpected = sorted(set(self.context) - ALLOWED_CONTEXT_FIELDS)
        if unexpected:
            raise ValueError(
                f"handoff context contains forbidden fields: {', '.join(unexpected)}"
            )
        for field, values in self.context.items():
            _validate_string_sequence(values, field=field)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible, allowlisted representation."""
        return {
            "schema_version": 1,
            "envelope": self.envelope.to_dict(),
            "objective": self.objective,
            "constraints": list(self.constraints),
            "evidence_digests": list(self.evidence_digests),
            "context": {key: list(self.context[key]) for key in sorted(self.context)},
        }

    def to_bounded_json(self, *, max_bytes: int = DEFAULT_MAX_HANDOFF_BYTES) -> str:
        """Serialize deterministically and reject payloads above the byte budget."""
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        rendered = json.dumps(
            self.to_dict(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        size = len(rendered.encode("utf-8"))
        if size > max_bytes:
            raise ValueError(f"handoff exceeds byte budget: {size} > {max_bytes}")
        return rendered
