"""Dataclass bundles for composite runtime support assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.composite.aggregator import EnricherAggregator
    from bioetl.application.composite.checkpoint import CompositeCheckpointService
    from bioetl.application.composite.coalesce_policy import CoalescePolicyService
    from bioetl.application.composite.column_orderer import ColumnOrderer
    from bioetl.application.composite.column_priority_orderer import (
        ColumnPriorityOrderer,
    )
    from bioetl.application.composite.column_renamer import ColumnRenamer
    from bioetl.application.composite.conflict_resolver import ConflictResolverService
    from bioetl.application.composite.coordinator import EnrichmentCoordinatorService
    from bioetl.application.composite.deduplication import (
        EnricherDeduplicatorService,
    )
    from bioetl.application.composite.dependency_coordinator import (
        DependencyCoordinatorService,
    )
    from bioetl.application.composite.fsm_helper import FSMStateHelperService
    from bioetl.application.composite.join_planner import JoinPlannerService
    from bioetl.application.composite.key_extractor import KeyExtractorService
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.ports import QuarantinePort


@dataclass(slots=True)
class ExecutionSupportServicesBundle:
    """Execution-facing services shared across composite runtime phases."""

    key_extractor: KeyExtractorService
    dependency_coordinator: DependencyCoordinatorService
    coordinator: EnrichmentCoordinatorService


@dataclass(slots=True)
class RuntimeManagementServicesBundle:
    """Checkpoint, FSM, DQ, and quarantine services for runtime orchestration."""

    checkpoint_manager: CompositeCheckpointService
    dq_report_service: DQReportService
    fsm_state_helper: FSMStateHelperService
    quarantine_port: QuarantinePort | None


@dataclass(slots=True)
class MergeDependenciesBundle:
    """Merge-specific collaborators assembled in composition."""

    deduplicator: EnricherDeduplicatorService
    aggregator: EnricherAggregator
    renamer: ColumnRenamer
    orderer: ColumnOrderer
    priority_orderer: ColumnPriorityOrderer
    coalesce_policy: CoalescePolicyService
    conflict_resolver: ConflictResolverService
    join_planner: JoinPlannerService


__all__ = [
    "ExecutionSupportServicesBundle",
    "MergeDependenciesBundle",
    "RuntimeManagementServicesBundle",
]
