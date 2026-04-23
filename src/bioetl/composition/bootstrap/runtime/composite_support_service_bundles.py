"""Dataclass bundles for composite runtime support assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_wiring_api import (
        CoalescePolicyService,
        ColumnOrderService,
        ColumnPriorityOrderer,
        ColumnRenamer,
        CompositeCheckpointService,
        ConflictResolverService,
        DependencyCoordinatorService,
        EnricherAggregator,
        EnricherDeduplicatorService,
        EnrichmentCoordinatorService,
        FSMStateHelperService,
        JoinPlannerService,
        KeyExtractorService,
    )
    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
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


@dataclass(frozen=True, slots=True)
class CompositeControlPlaneBundle:
    """Optional control-plane artifacts materialized for one composite run."""

    manifest_id: str | None = None
    execution_fingerprint: str | None = None
    run_ledger_service: RunLedgerService | None = None
    config_hash: str | None = None
    resolved_config_hash: str | None = None
    effective_config_hash: str | None = None
    dq_contract_compatibility_hash: str | None = None
    effective_config_artifact_id: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None


@dataclass(slots=True)
class MergeDependenciesBundle:
    """Merge-specific collaborators assembled in composition."""

    deduplicator: EnricherDeduplicatorService
    aggregator: EnricherAggregator
    renamer: ColumnRenamer
    orderer: ColumnOrderService | None
    priority_orderer: ColumnPriorityOrderer | None
    order_service: ColumnOrderService
    coalesce_policy: CoalescePolicyService
    conflict_resolver: ConflictResolverService
    join_planner: JoinPlannerService


__all__ = [
    "CompositeControlPlaneBundle",
    "ExecutionSupportServicesBundle",
    "MergeDependenciesBundle",
    "RuntimeManagementServicesBundle",
]
