"""Merge-dependency bundle for composite runtime assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_wiring_api import (
        CoalescePolicyService,
        ColumnOrderService,
        ColumnRenamer,
        ConflictResolverService,
        EnricherAggregator,
        EnricherDeduplicatorService,
        JoinPlannerService,
    )


@dataclass(slots=True)
class MergeDependenciesBundle:
    """Merge-specific collaborators assembled in composition."""

    deduplicator: EnricherDeduplicatorService
    aggregator: EnricherAggregator
    renamer: ColumnRenamer
    order_service: ColumnOrderService
    coalesce_policy: CoalescePolicyService
    conflict_resolver: ConflictResolverService
    join_planner: JoinPlannerService


__all__ = ["MergeDependenciesBundle"]
