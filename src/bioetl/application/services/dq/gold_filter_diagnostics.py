"""Resolve bounded Gold eligibility diagnostics for accounting and debug export."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.filtering import FilterDecision
from bioetl.domain.run_reports.context import get_stage_accounting

if TYPE_CHECKING:
    from bioetl.application.core.protocols import GoldFilterCallback


def resolve_gold_filter_details(
    gold_filter: GoldFilterCallback,
    record: dict[str, object],
) -> dict[str, object] | None:
    """Record exclusion rule diagnostics in the active accounting context."""
    details = _evaluate_gold_filter_details(gold_filter, record)
    accounting = get_stage_accounting()
    if accounting is not None:
        accounting.record_gold_filter_rejection(details or {})
    return details


def _evaluate_gold_filter_details(
    gold_filter: GoldFilterCallback,
    record: dict[str, object],
) -> dict[str, object] | None:
    """Resolve structured Gold-filter exclusion details when available.

    Prefers a bound-method owner that exposes a public ``gold_filters``
    evaluator (``evaluate`` → ``FilterDecision``). Falls back to the
    historical ``_gold_filters`` attribute for reverse compatibility.
    """
    owner = getattr(gold_filter, "__self__", None)
    if owner is None:
        return None
    gold_filters = getattr(owner, "gold_filters", None)
    if gold_filters is None:
        gold_filters = getattr(owner, "_gold_filters", None)
    evaluate = getattr(gold_filters, "evaluate", None)
    if not callable(evaluate):
        return None
    decision = evaluate(record)
    if isinstance(decision, FilterDecision) and not decision.include:
        return decision.to_dict()
    return None
