"""Composite replay evidence helpers shared by manifest diagnostics."""

from __future__ import annotations

from bioetl.domain.control_plane.run_ledger import (
    COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
    COMPOSITE_ENRICHER_COMPLETED_EVENT,
    COMPOSITE_MERGE_COMPLETED_EVENT,
    RunLedgerEntry,
)

_RICH_COMPOSITE_REPLAY_EVENTS = frozenset(
    {
        COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
        COMPOSITE_ENRICHER_COMPLETED_EVENT,
        COMPOSITE_MERGE_COMPLETED_EVENT,
    }
)


def attach_rich_composite_replay_support(
    summary: dict[str, object],
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> dict[str, object]:
    """Mark composite rich replay support only when ledger evidence is present."""
    observed_events = {
        entry.event_type
        for entry in ledger_entries
        if entry.event_type in _RICH_COMPOSITE_REPLAY_EVENTS
    }
    if not _RICH_COMPOSITE_REPLAY_EVENTS.issubset(observed_events):
        return summary
    updated = dict(summary)
    updated["composite_resume_rich_replay_supported"] = True
    return updated


__all__ = ["attach_rich_composite_replay_support"]
