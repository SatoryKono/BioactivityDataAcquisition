"""Pure claim-building helpers for historical replay closure."""

from __future__ import annotations

from typing import Protocol, cast

from bioetl.application.services.control_plane.replay.historical_closure_models import (
    HistoricalReplayClaimScopeMode as HistoricalReplayClaimScopeMode,
)
from bioetl.application.services.control_plane.replay.historical_closure_models import (
    HistoricalReplayResidualDispositionRecord as HistoricalReplayResidualDispositionRecord,
)


class _ManifestRecord(Protocol):
    manifest_id: str


def _record_manifest_id(record: object) -> str | None:
    if not hasattr(record, "manifest_id"):
        return None
    return cast(_ManifestRecord, record).manifest_id


def build_narrowed_scope_global_claim(
    *,
    unresolved_records: tuple[object, ...],
    narrowed_scope_blockers: tuple[str, ...],
) -> dict[str, object]:
    """Build a retained-certifiable-scope claim gate."""
    claimed = not unresolved_records and not narrowed_scope_blockers
    if claimed:
        reason = (
            "retained_certifiable_historical_scope_has_no_remaining_unresolved_runs"
        )
    elif unresolved_records:
        reason = "residual_historical_runs_lack_explicit_resolution_disposition"
    else:
        reason = "retained_certifiable_scope_still_contains_in_scope_blockers"
    blocked_manifest_ids = [
        *[
            manifest_id
            for record in unresolved_records
            if (manifest_id := _record_manifest_id(record)) is not None
        ],
        *narrowed_scope_blockers,
    ]
    return {
        "claimed": claimed,
        "verdict": "claim_supported" if claimed else "claim_blocked",
        "reason": reason,
        "scope": "retained_certifiable_historical_runs",
        "blocked_manifest_ids": blocked_manifest_ids,
    }


def has_irrecoverable_dispositions(
    disposition_map: dict[str, HistoricalReplayResidualDispositionRecord],
) -> bool:
    """Return whether any residual disposition is explicitly irrecoverable."""
    return any(
        disposition.disposition == "irrecoverable_missing_immutable_evidence"
        for disposition in disposition_map.values()
    )


def universal_scope_claim_supported(
    *,
    inventory: object,
    unresolved_records: tuple[object, ...],
    has_irrecoverable: bool,
) -> bool:
    """Return whether all retained historical runs support universal replay claim."""
    manifest_count = int(getattr(inventory, "manifest_count", 0))
    certified_count = int(getattr(inventory, "certified_count", 0))
    replayable_count = int(getattr(inventory, "replayable_count", 0))
    unsupported_count = int(getattr(inventory, "unsupported_count", 0))
    return (
        manifest_count > 0
        and certified_count + replayable_count == manifest_count
        and unsupported_count == 0
        and not unresolved_records
        and not has_irrecoverable
    )


def universal_scope_claim_block_reason(
    *,
    unresolved_records: tuple[object, ...],
    has_irrecoverable: bool,
    unsupported_count: int,
) -> str:
    """Resolve the deterministic block reason for a universal replay claim."""
    if unresolved_records:
        return "residual_historical_runs_lack_explicit_resolution_disposition"
    if has_irrecoverable:
        return "irrecoverable_legacy_runs_block_universal_historical_claim"
    if unsupported_count:
        return "some_retained_runs_remain_outside_supported_historical_scope"
    return "historical_replay_closure_program_not_yet_completed"


def build_universal_scope_global_claim(
    *,
    inventory: object,
    unresolved_records: tuple[object, ...],
    disposition_map: dict[str, HistoricalReplayResidualDispositionRecord],
) -> dict[str, object]:
    """Build an all-retained-historical-runs claim gate."""
    has_irrecoverable = has_irrecoverable_dispositions(disposition_map)
    claimed = universal_scope_claim_supported(
        inventory=inventory,
        unresolved_records=unresolved_records,
        has_irrecoverable=has_irrecoverable,
    )
    if claimed:
        reason = "all_retained_historical_runs_have_exact_replay_evidence_or_certified_parent_state"
    else:
        reason = universal_scope_claim_block_reason(
            unresolved_records=unresolved_records,
            has_irrecoverable=has_irrecoverable,
            unsupported_count=int(getattr(inventory, "unsupported_count", 0)),
        )
    return {
        "claimed": claimed,
        "verdict": "claim_supported" if claimed else "claim_blocked",
        "reason": reason,
        "scope": "all_retained_historical_runs",
        "blocked_manifest_ids": [
            manifest_id
            for record in unresolved_records
            if (manifest_id := _record_manifest_id(record)) is not None
        ],
    }


__all__ = [
    "build_narrowed_scope_global_claim",
    "build_universal_scope_global_claim",
    "has_irrecoverable_dispositions",
    "universal_scope_claim_block_reason",
    "universal_scope_claim_supported",
]
