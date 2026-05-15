"""Direct tests for pure historical replay universe policy helpers."""

from __future__ import annotations

from bioetl.application.services.control_plane.historical_replay_universe_policy import (
    build_durable_coverage_claim,
    build_universal_claim,
)
from bioetl.application.services.control_plane.historical_replay_universe_service import (
    HistoricalReplayUniverseInventorySnapshot,
    HistoricalReplayUniverseRecord,
)


def _record(
    *,
    manifest_id: str,
    certification_status: str,
    durable_evidence_coverage: bool,
) -> HistoricalReplayUniverseRecord:
    return HistoricalReplayUniverseRecord(
        manifest_id=manifest_id,
        run_id=f"run-{manifest_id}",
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        execution_context="isolated",
        certification_status=certification_status,
        replay_occurrence_kind="ordinary_live_capture",
        blocking_reasons=(),
        universe_origin="external_archived",
        evidence_residency="archive_tier",
        durable_evidence_coverage=durable_evidence_coverage,
        source_pack_ref="archive-pack",
    )


def test_build_universal_claim_collects_unresolved_manifest_ids() -> None:
    inventory = HistoricalReplayUniverseInventorySnapshot(
        records=(
            _record(
                manifest_id="manifest-open",
                certification_status="awaiting_source_snapshot_certification",
                durable_evidence_coverage=False,
            ),
            _record(
                manifest_id="manifest-closed",
                certification_status="already_certified",
                durable_evidence_coverage=True,
            ),
        )
    )

    assert build_universal_claim(inventory) == {
        "claimed": False,
        "verdict": "claim_blocked",
        "reason": "known_historical_universe_still_contains_unresolved_replay_blockers",
        "scope": "all_known_historical_runs",
        "blocked_manifest_ids": ["manifest-open"],
    }


def test_build_durable_coverage_claim_blocks_on_non_durable_records() -> None:
    inventory = HistoricalReplayUniverseInventorySnapshot(
        records=(
            _record(
                manifest_id="manifest-open",
                certification_status="already_certified",
                durable_evidence_coverage=False,
            ),
        )
    )

    assert build_durable_coverage_claim(inventory) == {
        "claimed": False,
        "verdict": "claim_blocked",
        "reason": "known_historical_universe_still_contains_non_durable_evidence_paths",
        "scope": "all_known_historical_runs",
        "blocked_manifest_ids": ["manifest-open"],
    }
