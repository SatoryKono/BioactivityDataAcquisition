"""Legacy ledger event value object for storage contract tests."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    """Minimal append-only ledger event payload."""

    event_type: str
    timestamp: str
    run_id: str
    data: dict[str, object] = field(default_factory=dict)


__all__ = ["LedgerEvent"]
