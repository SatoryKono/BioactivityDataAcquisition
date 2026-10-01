"""Collaborator bundle for ``MergeService``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.application.composite.aggregator import EnricherAggregator
    from bioetl.application.composite.coalesce_policy import CoalescePolicyService
    from bioetl.application.composite.column_renamer import ColumnRenamer
    from bioetl.application.composite.column_service import ColumnOrderService
    from bioetl.application.composite.conflict_resolver import ConflictResolverService
    from bioetl.application.composite.deduplication import EnricherDeduplicatorService
    from bioetl.application.composite.join_planner import JoinPlannerService
    from bioetl.domain.composite import MergeConfig
    from bioetl.domain.ports import LoggerPort

__all__ = ["MergeCollaboratorGroup"]


class _MergeIOHost(Protocol):
    """Required host dependencies initialized by ``MergeService``."""

    _config: MergeConfig
    _logger: LoggerPort
    _join_planner: JoinPlannerService


@dataclass(frozen=True, slots=True)
class MergeCollaboratorGroup:
    """Bundle of merge-time collaborators wired in composition."""

    deduplicator: EnricherDeduplicatorService
    aggregator: EnricherAggregator
    renamer: ColumnRenamer
    order_service: ColumnOrderService
    coalesce_policy: CoalescePolicyService
    conflict_resolver: ConflictResolverService
    join_planner: JoinPlannerService
