"""Module-level conservation projectors for stage accounting rows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeGuard

from bioetl.domain.run_reports.models import BalanceStatus, TrackingCoverage

__all__ = [
    "REPORT_LAYER_FIELDS",
    "_is_degraded_balance",
    "_is_unknown_balance",
    "_layer_removed_budget",
    "_prefer_conserving_projection",
    "_resolve_balance_status",
    "reconcile_saved_layer_counts",
]

_SILVER_LAYER_FIELDS = (
    "silver_valid",
    "silver_filtered_out",
    "silver_quarantined",
    "silver_skipped",
    "silver_deduplicated",
)
_GOLD_LAYER_FIELDS = (
    "gold_written",
    "gold_excluded_by_contract",
    "gold_quarantined",
    "gold_skipped",
    "gold_deduplicated",
)
REPORT_LAYER_FIELDS = ("bronze_records", *_SILVER_LAYER_FIELDS, *_GOLD_LAYER_FIELDS)


def reconcile_saved_layer_counts(
    report: Mapping[str, object] | None,
    *,
    run_id: str,
    manifest_id: str,
    pipeline: str,
    run_types: tuple[str, ...],
    known_counts: Mapping[str, int | float | None],
) -> dict[str, int]:
    """Return complete, conserved counts from matching saved-run evidence."""
    sections = _saved_report_sections(report)
    if sections is None:
        return {}
    identity, layers = sections
    expected_identity = {
        "run_id": run_id,
        "manifest_id": manifest_id,
        "pipeline_name": pipeline,
    }
    if not _saved_identity_matches(identity, expected_identity, run_types):
        return {}
    return _conserved_layer_counts(layers, known_counts)


def _saved_report_sections(
    report: Mapping[str, object] | None,
) -> tuple[Mapping[str, object], Mapping[str, object]] | None:
    """Read the two required sections only from fully tracked evidence."""
    if not report or report.get("tracking_coverage") != "full":
        return None
    identity, layers = report.get("identity"), report.get("layers")
    if not isinstance(identity, dict) or not isinstance(layers, dict):
        return None
    return identity, layers


def _saved_identity_matches(
    identity: Mapping[str, object],
    expected: Mapping[str, str],
    run_types: tuple[str, ...],
) -> bool:
    """Match the selected run, manifest, pipeline and optional run-type scope."""
    if any(identity.get(field) != value for field, value in expected.items()):
        return False
    return not run_types or identity.get("run_type") in run_types


def _valid_saved_count(count: object, known: int | float | None) -> TypeGuard[int]:
    """Accept explicit nonnegative integers consistent with ledger evidence."""
    return type(count) is int and count >= 0 and (known is None or known == count)


def _saved_layers_balance(observed: Mapping[str, int]) -> bool:
    """Conserve records independently across Silver and Gold."""
    silver_total = sum(observed[field] for field in _SILVER_LAYER_FIELDS)
    gold_total = sum(observed[field] for field in _GOLD_LAYER_FIELDS)
    return (
        silver_total == observed["bronze_records"]
        and gold_total == observed["silver_valid"]
    )


def _conserved_layer_counts(
    layers: Mapping[str, object],
    known_counts: Mapping[str, int | float | None],
) -> dict[str, int]:
    observed: dict[str, int] = {}
    for field in REPORT_LAYER_FIELDS:
        count = layers.get(field)
        known = known_counts.get(field)
        if not _valid_saved_count(count, known):
            return {}
        observed[field] = count
    if not _saved_layers_balance(observed):
        return {}
    return observed


def _is_unknown_balance(records_in: int, tracking: TrackingCoverage) -> bool:
    return records_in == 0 and tracking is TrackingCoverage.NOT_TRACKED


def _is_degraded_balance(unaccounted: int, tracking: TrackingCoverage) -> bool:
    return unaccounted > 0 and tracking is TrackingCoverage.PARTIAL


def _layer_removed_budget(*, removed_mapped: int, default_removed: int) -> int:
    """Prefer explicitly mapped removals over the layer default."""
    if removed_mapped > 0:
        return removed_mapped
    return default_removed


def _prefer_conserving_projection(
    *,
    records_in: int,
    records_out: int,
    removed_total: int,
    default_in: int,
    default_out: int,
    default_removed: int,
    removed_mapped: int,
) -> tuple[int, int, int]:
    """Prefer layer-aligned in/out when bucket values break conservation.

    High-volume hooks may over-count ``records_out`` (e.g. gold batch
    metrics). Layer totals from RunResult remain the coarse SoT for
    funnel geometry; removal reason maps still come from the bucket.

    Over-accounted removals (``removed_mapped`` above the layer budget)
    MUST remain visible as FAILING — do not rewrite geometry to hide them.
    """
    if records_in == records_out + removed_total:
        return records_in, records_out, removed_total
    if removed_mapped > default_removed > 0:
        return records_in, records_out, removed_total
    layer_removed = _layer_removed_budget(
        removed_mapped=removed_mapped, default_removed=default_removed
    )
    if default_in > 0 and default_in == default_out + layer_removed:
        return default_in, default_out, layer_removed
    return records_in, records_out, removed_total


def _resolve_balance_status(
    *,
    records_in: int,
    records_out: int,
    removed_total: int,
    unaccounted: int,
    tracking: TrackingCoverage,
) -> BalanceStatus:
    """Resolve the conservation balance status for one funnel row."""
    if records_in == records_out + removed_total:
        return BalanceStatus.OK
    if _is_unknown_balance(records_in, tracking):
        return BalanceStatus.UNKNOWN
    if _is_degraded_balance(unaccounted, tracking):
        return BalanceStatus.DEGRADED
    return BalanceStatus.FAILING


def accounting_conflicts(reconciliation: object, verdict: object) -> list[str]:
    """Name saved silver/gold accounting failures. The ERROR override is intentional."""
    if not isinstance(reconciliation, dict):
        return []
    conflicts: list[str] = []
    for stage in ("silver", "gold"):
        prior = "bronze" if stage == "silver" else "silver"
        key = f"{stage}_vs_{prior}_status"
        if reconciliation.get(key) == "FAILING":
            conflicts.append(
                f"Saved report accounting conflict: {key}=FAILING, "
                f"delta={reconciliation.get(f'{stage}_delta', 'UNKNOWN')}. "
                f"Saved Trust verdict: {verdict}; inspect report and ledger."
            )
    return conflicts


def _stage_accounting_conflicts(funnel: object, verdict: object) -> list[str]:
    """Name funnel rows whose own balance is FAILING."""
    if not isinstance(funnel, list):
        return []
    conflicts: list[str] = []
    for stage in funnel:
        if not isinstance(stage, dict) or stage.get("balance_status") != "FAILING":
            continue
        conflicts.append(
            "Saved report stage accounting conflict: "
            f"{stage.get('stage_id', 'UNKNOWN')} balance=FAILING, "
            f"unaccounted={stage.get('unaccounted', 'UNKNOWN')}. "
            f"Saved Trust verdict: {verdict}; inspect report and ledger."
        )
    return conflicts


def saved_trust_fields(
    *,
    verdict: object,
    reasons_text: str,
    reconciliation: object,
    funnel: object = None,
) -> dict[str, object]:
    """Keep the saved control verdict and surface an intentional ERROR override."""
    conflicts = [
        *accounting_conflicts(reconciliation, verdict),
        *_stage_accounting_conflicts(funnel, verdict),
    ]
    if conflicts:
        reasons_text = "\n".join(filter(None, (reasons_text, *conflicts)))
    return {
        "trust_status": "ERROR" if conflicts else verdict,
        "saved_trust_status": verdict,
        "accounting_integrity": "CONFLICT" if conflicts else "NO REPORTED CONFLICT",
        "reasons_text": reasons_text,
    }
