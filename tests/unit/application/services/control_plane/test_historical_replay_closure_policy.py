"""Direct tests for pure historical replay closure policy helpers."""

from __future__ import annotations

import pytest

from bioetl.application.services.control_plane.replay.historical_closure_models import (
    HistoricalReplayResidualDispositionRecord,
)
from bioetl.application.services.control_plane.replay.historical_closure_policy import (
    build_retained_corpus_claim,
    build_suggested_resolution,
    narrowed_scope_blockers,
    resolve_closure_verdict,
    validate_residual_dispositions,
)
from bioetl.application.services.control_plane.replay.historical_corpus_models import (
    HistoricalReplayCertifiabilityInventory,
    HistoricalReplayCertifiabilityRecord,
)


def _record(
    *,
    manifest_id: str,
    certification_status: str,
    blocking_reasons: tuple[str, ...] = (),
) -> HistoricalReplayCertifiabilityRecord:
    return HistoricalReplayCertifiabilityRecord(
        manifest_id=manifest_id,
        run_id=f"run-{manifest_id}",
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        execution_context="isolated",
        family="chembl.activity",
        certification_scope="retained",
        certification_status=certification_status,
        replay_occurrence_kind="ordinary_live_capture",
        broader_historical_exact_replay_policy="certified_historical_exact_replay_tranche_supported",
        broader_historical_exact_replay_boundary="historical_source_snapshot_certification",
        broader_historical_exact_replay_state="outside_launch_time_snapshot_boundary",
        blocking_reasons=blocking_reasons,
    )


def test_validate_residual_dispositions_rejects_unknown_manifest() -> None:
    blocked_records = (
        _record(
            manifest_id="manifest-1",
            certification_status="awaiting_source_snapshot_certification",
        ),
    )

    disposition = HistoricalReplayResidualDispositionRecord(
        manifest_id="manifest-2",
        disposition="manual_review_required",
        rationale="not blocked here",
    )

    try:
        validate_residual_dispositions(
            blocked_records=blocked_records,
            residual_dispositions=(disposition,),
        )
    except ValueError as exc:
        assert "not currently blocked" in str(exc)
    else:
        pytest.fail("Expected ValueError for non-blocked residual disposition")


def test_resolve_closure_verdict_supports_scope_narrowing() -> None:
    inventory = HistoricalReplayCertifiabilityInventory(
        records=(
            _record(
                manifest_id="manifest-1",
                certification_status="outside_certified_historical_scope",
            ),
        )
    )
    disposition_map = {
        "manifest-1": HistoricalReplayResidualDispositionRecord(
            manifest_id="manifest-1",
            disposition="outside_universal_claim_scope",
            rationale="explicit legacy narrowing",
        )
    }

    verdict = resolve_closure_verdict(
        inventory=inventory,
        unresolved_records=(),
        disposition_map=disposition_map,
        claim_scope_mode="retained_certifiable_historical_runs",
    )

    assert verdict == (
        "scope_narrowed_closed",
        "retained_certifiable_historical_scope_is_closed_after_explicit_legacy_scope_narrowing",
    )
    assert narrowed_scope_blockers(disposition_map) == ()


def test_build_retained_corpus_claim_blocks_on_unresolved_records() -> None:
    inventory = HistoricalReplayCertifiabilityInventory(
        records=(
            _record(
                manifest_id="manifest-1",
                certification_status="awaiting_certified_source_lineage",
            ),
        )
    )
    unresolved_records = (inventory.records[0],)

    assert build_retained_corpus_claim(
        inventory=inventory,
        unresolved_records=unresolved_records,
    ) == {
        "claimed": False,
        "verdict": "claim_blocked",
        "reason": "retained_corpus_still_contains_blocked_or_out_of_scope_runs",
        "scope": "retained_control_plane_corpus",
    }


def test_build_suggested_resolution_maps_status_to_disposition() -> None:
    record = _record(
        manifest_id="manifest-1",
        certification_status="awaiting_certified_source_lineage",
        blocking_reasons=("composite_parent_missing",),
    )

    assert build_suggested_resolution(record) == {
        "manifest_id": "manifest-1",
        "run_id": "run-manifest-1",
        "certification_status": "awaiting_certified_source_lineage",
        "suggested_disposition": "certify_upstream_source_lineage",
        "blocking_reasons": ["composite_parent_missing"],
    }
