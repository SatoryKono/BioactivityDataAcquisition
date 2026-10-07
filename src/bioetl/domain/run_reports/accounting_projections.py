"""Module-level conservation projectors for stage accounting rows."""

from __future__ import annotations

from bioetl.domain.run_reports.models import BalanceStatus, TrackingCoverage

__all__ = [
    "_is_degraded_balance",
    "_is_unknown_balance",
    "_layer_removed_budget",
    "_prefer_conserving_projection",
    "_resolve_balance_status",
]


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


def saved_trust_fields(
    *,
    verdict: object,
    reasons_text: str,
    reconciliation: object,
) -> dict[str, object]:
    """Keep the saved control verdict and surface an intentional ERROR override."""
    conflicts = accounting_conflicts(reconciliation, verdict)
    if conflicts:
        reasons_text = "\n".join(filter(None, (reasons_text, *conflicts)))
    return {
        "trust_status": "ERROR" if conflicts else verdict,
        "saved_trust_status": verdict,
        "accounting_integrity": "CONFLICT" if conflicts else "NO REPORTED CONFLICT",
        "reasons_text": reasons_text,
    }
