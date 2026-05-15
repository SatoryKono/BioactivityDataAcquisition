"""Pure policy helpers for full-universe historical replay reporting."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.historical_replay_universe_service import (
        HistoricalReplayUniverseInventorySnapshot,
    )

__all__ = [
    "build_authoritative_truth_surface",
    "build_durable_coverage_claim",
    "build_universal_claim",
    "build_universe_report_id",
]

_CLOSED_CERTIFICATION_STATUSES = frozenset({"already_replayable", "already_certified"})


def build_authoritative_truth_surface() -> dict[str, object]:
    """Return the canonical truth surface for literal any-run replay claims."""
    return {
        "surface": "historical_replay_universe_closure_report",
        "scope": "all_known_historical_runs",
        "claim_kind": "literal_any_run_exact_replay",
        "authoritative": True,
        "required_inputs": (
            "local_retained_control_plane_inventory",
            "external_archived_universe_records",
            "durable_evidence_coverage_verdicts",
            "historical_replay_certification_statuses",
        ),
    }


def build_universal_claim(
    inventory: HistoricalReplayUniverseInventorySnapshot,
) -> dict[str, object]:
    blocked = [
        record.manifest_id
        for record in inventory.records
        if record.certification_status not in _CLOSED_CERTIFICATION_STATUSES
    ]
    claimed = inventory.manifest_count > 0 and not blocked
    return {
        "claimed": claimed,
        "verdict": "claim_supported" if claimed else "claim_blocked",
        "reason": (
            "all_known_historical_runs_are_exact_replayable"
            if claimed
            else "known_historical_universe_still_contains_unresolved_replay_blockers"
        ),
        "scope": "all_known_historical_runs",
        "blocked_manifest_ids": blocked,
    }


def build_durable_coverage_claim(
    inventory: HistoricalReplayUniverseInventorySnapshot,
) -> dict[str, object]:
    blocked = [
        record.manifest_id
        for record in inventory.records
        if not record.durable_evidence_coverage
    ]
    claimed = inventory.manifest_count > 0 and not blocked
    return {
        "claimed": claimed,
        "verdict": "claim_supported" if claimed else "claim_blocked",
        "reason": (
            "every_known_historical_run_has_durable_evidence_coverage"
            if claimed
            else "known_historical_universe_still_contains_non_durable_evidence_paths"
        ),
        "scope": "all_known_historical_runs",
        "blocked_manifest_ids": blocked,
    }


def build_universe_report_id(
    *,
    inventory: HistoricalReplayUniverseInventorySnapshot,
    authoritative_truth_surface: dict[str, object],
    universal_claim: dict[str, object],
    durable_claim: dict[str, object],
) -> str:
    payload = {
        "inventory": inventory.to_dict(),
        "authoritative_truth_surface": authoritative_truth_surface,
        "universal_claim": universal_claim,
        "durable_evidence_coverage_claim": durable_claim,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"historical-replay-universe-{digest[:16]}"
