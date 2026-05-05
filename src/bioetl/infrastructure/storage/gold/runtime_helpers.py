"""Runtime dependency resolution helpers for ``GoldWriter``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.ports.noop import NoOpMetadataWriter

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        AuditPort,
        LineageStorePort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
        MetricsPort,
        TracingPort,
    )
    from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
    from bioetl.infrastructure.export.csv_exporter_contract import CsvExporterPort


@dataclass(frozen=True, slots=True)
class GoldWriterRuntimeServices:
    """Grouped runtime collaborators for ``GoldWriter``."""

    csv_exporter: CsvExporterPort | None
    tracing: TracingPort | None
    metrics: MetricsPort | None
    audit: AuditPort | None
    metadata_writer: MetadataWriterPort
    metadata_coordinator: MetadataCoordinatorPort | None
    lineage_store: LineageStorePort | None
    contract_rollout_policy: ContractRolloutPolicy | None = None


def build_gold_writer_runtime_services(
    *,
    csv_exporter: CsvExporterPort | None,
    tracing: TracingPort | None,
    metrics: MetricsPort | None,
    audit: AuditPort | None,
    metadata_writer: MetadataWriterPort | None,
    metadata_coordinator: MetadataCoordinatorPort | None,
    lineage_store: LineageStorePort | None,
    contract_rollout_policy: ContractRolloutPolicy | None = None,
) -> GoldWriterRuntimeServices:
    """Build grouped runtime collaborators while preserving default resolution."""
    return GoldWriterRuntimeServices(
        csv_exporter=csv_exporter,
        tracing=tracing,
        metrics=metrics,
        audit=audit,
        metadata_writer=metadata_writer or NoOpMetadataWriter(),
        metadata_coordinator=metadata_coordinator,
        lineage_store=lineage_store,
        contract_rollout_policy=contract_rollout_policy,
    )
