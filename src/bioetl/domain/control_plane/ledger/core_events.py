"""Legacy ledger event value object for storage contract tests."""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.domain.serialization import (
    deserialize_from_json,
    serialize_to_json_canonical,
)


def _canonicalize_mapping(value: dict[str, object]) -> dict[str, object]:
    """Return a mapping with recursively sorted keys for replay-safe serialization."""
    canonical = deserialize_from_json(serialize_to_json_canonical(value))
    if not isinstance(canonical, dict):
        raise TypeError("Ledger event data must serialize to a JSON object")
    return canonical


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    """Minimal append-only ledger event payload."""

    event_type: str
    timestamp: str
    run_id: str
    data: dict[str, object] = field(default_factory=dict)

    def to_mapping(self) -> dict[str, object]:
        """Return a deterministic mapping suitable for canonical JSON replay."""
        return {
            "data": _canonicalize_mapping(dict(self.data)),
            "event_type": self.event_type,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
        }


__all__ = ["LedgerEvent"]
