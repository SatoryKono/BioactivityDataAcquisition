"""Pure policy helpers for historical replay closure workflows."""

from __future__ import annotations

import hashlib
import json

from bioetl.application.services.control_plane.replay.closure_claims import (
    HistoricalReplayClaimScopeMode,
    HistoricalReplayResidualDispositionRecord,
    build_narrowed_scope_global_claim,
    build_universal_scope_global_claim,
)
from bioetl.application.services.control_plane.replay.historical_corpus_models import (
    HistoricalReplayCertifiabilityInventory,
    HistoricalReplayCertifiabilityRecord,
)

__all__ = [
    "build_closure_report_id",
    "build_global_claim_gate",
    "build_retained_corpus_claim",
    "build_suggested_resolution",
    "narrowed_scope_blockers",
    "resolve_closure_verdict",
    "validate_residual_dispositions",
]


def validate_residual_dispositions(
    *,
    blocked_records: tuple[HistoricalReplayCertifiabilityRecord, ...],
    residual_dispositions: tuple[HistoricalReplayResidualDispositionRecord, ...],
) -> dict[str, HistoricalReplayResidualDispositionRecord]:
    blocked_ids = {record.manifest_id for record in blocked_records}
    disposition_map: dict[str, HistoricalReplayResidualDispositionRecord] = {}
    for disposition in residual_dispositions:
        if disposition.manifest_id not in blocked_ids:
            raise ValueError(
                "Historical replay residual disposition references a manifest "
                f"that is not currently blocked: {disposition.manifest_id!r}"
            )
        if disposition.manifest_id in disposition_map:
            raise ValueError(
                "Duplicate historical replay residual disposition for manifest "
                f"{disposition.manifest_id!r}"
            )
        disposition_map[disposition.manifest_id] = disposition
    return disposition_map


def resolve_closure_verdict(
    *,
    inventory: HistoricalReplayCertifiabilityInventory,
    unresolved_records: tuple[HistoricalReplayCertifiabilityRecord, ...],
    disposition_map: dict[str, HistoricalReplayResidualDispositionRecord],
    claim_scope_mode: HistoricalReplayClaimScopeMode,
) -> tuple[str, str]:
    if inventory.manifest_count == 0:
        return (
            "no_retained_historical_runs",
            "inventory_contains_no_retained_historical_runs",
        )
    if (
        inventory.certified_count + inventory.replayable_count
        == inventory.manifest_count
        and inventory.unsupported_count == 0
    ):
        return (
            "fully_closed",
            "all_retained_historical_runs_are_already_replayable_or_certified",
        )
    if unresolved_records:
        return (
            "residual_disposition_required",
            "blocked_historical_runs_require_explicit_resolution_disposition",
        )
    if (
        claim_scope_mode == "retained_certifiable_historical_runs"
        and narrowed_scope_blockers(disposition_map) == ()
    ):
        return (
            "scope_narrowed_closed",
            "retained_certifiable_historical_scope_is_closed_after_explicit_legacy_scope_narrowing",
        )
    if any(
        disposition.disposition == "irrecoverable_missing_immutable_evidence"
        for disposition in disposition_map.values()
    ):
        return (
            "residual_irrecoverable_subset_present",
            "some_historical_runs_remain_irrecoverable_without_trustworthy_immutable_evidence",
        )
    if inventory.unsupported_count:
        return (
            "outside_supported_scope_present",
            "some_retained_runs_remain_outside_the_current_supported_historical_replay_scope",
        )
    return (
        "residual_resolution_program_in_progress",
        "all_remaining_blocked_runs_have_explicit_resolution_tracks_but_not_yet_closed",
    )


def build_global_claim_gate(
    *,
    inventory: HistoricalReplayCertifiabilityInventory,
    unresolved_records: tuple[HistoricalReplayCertifiabilityRecord, ...],
    disposition_map: dict[str, HistoricalReplayResidualDispositionRecord],
    claim_scope_mode: HistoricalReplayClaimScopeMode,
) -> dict[str, object]:
    blockers = narrowed_scope_blockers(disposition_map)
    if claim_scope_mode == "retained_certifiable_historical_runs":
        return build_narrowed_scope_global_claim(
            unresolved_records=unresolved_records,
            narrowed_scope_blockers=blockers,
        )
    return build_universal_scope_global_claim(
        inventory=inventory,
        unresolved_records=unresolved_records,
        disposition_map=disposition_map,
    )


def narrowed_scope_blockers(
    disposition_map: dict[str, HistoricalReplayResidualDispositionRecord],
) -> tuple[str, ...]:
    excluded_dispositions = {
        "irrecoverable_missing_immutable_evidence",
        "outside_universal_claim_scope",
    }
    return tuple(
        sorted(
            manifest_id
            for manifest_id, disposition in disposition_map.items()
            if disposition.disposition not in excluded_dispositions
        )
    )


def build_retained_corpus_claim(
    *,
    inventory: HistoricalReplayCertifiabilityInventory,
    unresolved_records: tuple[HistoricalReplayCertifiabilityRecord, ...],
) -> dict[str, object]:
    claimed = (
        inventory.remaining_uncertified_count == 0
        and inventory.unsupported_count == 0
        and not unresolved_records
    )
    return {
        "claimed": claimed,
        "verdict": "claim_supported" if claimed else "claim_blocked",
        "reason": (
            "retained_corpus_has_no_remaining_uncertified_or_out_of_scope_runs"
            if claimed
            else "retained_corpus_still_contains_blocked_or_out_of_scope_runs"
        ),
        "scope": "retained_control_plane_corpus",
    }


def build_suggested_resolution(
    record: HistoricalReplayCertifiabilityRecord,
) -> dict[str, object]:
    return {
        "manifest_id": record.manifest_id,
        "run_id": record.run_id,
        "certification_status": record.certification_status,
        "suggested_disposition": _suggested_disposition(record),
        "blocking_reasons": list(record.blocking_reasons),
    }


def build_closure_report_id(
    *,
    inventory: HistoricalReplayCertifiabilityInventory,
    residual_dispositions: tuple[HistoricalReplayResidualDispositionRecord, ...],
    closure_verdict: str,
    closure_reason: str,
    claim_scope_mode: HistoricalReplayClaimScopeMode,
    global_claim: dict[str, object],
    retained_corpus_claim: dict[str, object],
) -> str:
    payload = {
        "inventory": inventory.to_dict(),
        "residual_dispositions": [
            disposition.to_dict()
            for disposition in sorted(
                residual_dispositions,
                key=lambda item: (item.manifest_id, item.disposition),
            )
        ],
        "closure_verdict": closure_verdict,
        "closure_reason": closure_reason,
        "claim_scope_mode": claim_scope_mode,
        "global_universal_historical_replay_claim": global_claim,
        "retained_corpus_claim": retained_corpus_claim,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"historical-replay-closure-{digest[:16]}"


def _suggested_disposition(
    record: HistoricalReplayCertifiabilityRecord,
) -> str:
    if record.certification_status == "awaiting_source_snapshot_certification":
        return "reconstruct_immutable_evidence"
    if record.certification_status == "awaiting_certified_source_lineage":
        return "certify_upstream_source_lineage"
    if record.certification_status == "outside_certified_historical_scope":
        return "outside_universal_claim_scope"
    return "manual_review_required"
