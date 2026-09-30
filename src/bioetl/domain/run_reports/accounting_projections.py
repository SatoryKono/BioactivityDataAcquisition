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
