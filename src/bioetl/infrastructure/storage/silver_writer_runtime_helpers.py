"""Runtime dependency resolution helpers for ``SilverWriter``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.medallion import WriteModePolicy
from bioetl.domain.ports import NoOpMetadataWriter, NoOpTracing
from bioetl.domain.services.dq_metrics_calculator import DQMetricsCalculator
from bioetl.infrastructure.storage.write_resilience import (
    DEFAULT_SILVER_MERGE_POLICY,
    SilverMergeResiliencePolicy,
)
from bioetl.infrastructure.validation.pandera_validator import NoOpSilverValidator

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        AuditPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.infrastructure.export.csv_exporter import CsvExporter


@dataclass(frozen=True, slots=True)
class SilverWriterRuntimeServices:
    """Grouped runtime collaborators for ``SilverWriter``."""

    csv_exporter: CsvExporter | None
    tracing: TracingPort
    write_policy: WriteModePolicy
    metrics: MetricsPort | None
    audit: AuditPort | None
    silver_validator: SilverValidatorPort
    metadata_writer: MetadataWriterPort
    metadata_coordinator: MetadataCoordinatorPort | None
    dq_calculator: DQMetricsCalculator
    merge_resilience_policy: SilverMergeResiliencePolicy


def resolve_silver_writer_runtime(
    *,
    tracing: TracingPort | None,
    write_policy: WriteModePolicy | None,
    silver_validator: SilverValidatorPort | None,
    metadata_writer: MetadataWriterPort | None,
    dq_calculator: DQMetricsCalculator | None,
    merge_resilience_policy: SilverMergeResiliencePolicy | None,
) -> tuple[
    TracingPort,
    WriteModePolicy,
    SilverValidatorPort,
    MetadataWriterPort,
    DQMetricsCalculator,
    SilverMergeResiliencePolicy,
]:
    """Resolve default runtime collaborators for ``SilverWriter``."""
    return (
        tracing or NoOpTracing(),
        write_policy or WriteModePolicy(),
        silver_validator or NoOpSilverValidator(),
        metadata_writer or NoOpMetadataWriter(),
        dq_calculator or DQMetricsCalculator(),
        merge_resilience_policy or DEFAULT_SILVER_MERGE_POLICY,
    )


def build_silver_writer_runtime_services(
    *,
    csv_exporter: CsvExporter | None,
    tracing: TracingPort | None,
    write_policy: WriteModePolicy | None,
    metrics: MetricsPort | None,
    audit: AuditPort | None,
    silver_validator: SilverValidatorPort | None,
    metadata_writer: MetadataWriterPort | None,
    metadata_coordinator: MetadataCoordinatorPort | None,
    dq_calculator: DQMetricsCalculator | None,
    merge_resilience_policy: SilverMergeResiliencePolicy | None,
) -> SilverWriterRuntimeServices:
    """Build grouped runtime collaborators while preserving default resolution."""
    (
        resolved_tracing,
        resolved_write_policy,
        resolved_silver_validator,
        resolved_metadata_writer,
        resolved_dq_calculator,
        resolved_merge_resilience_policy,
    ) = resolve_silver_writer_runtime(
        tracing=tracing,
        write_policy=write_policy,
        silver_validator=silver_validator,
        metadata_writer=metadata_writer,
        dq_calculator=dq_calculator,
        merge_resilience_policy=merge_resilience_policy,
    )
    return SilverWriterRuntimeServices(
        csv_exporter=csv_exporter,
        tracing=resolved_tracing,
        write_policy=resolved_write_policy,
        metrics=metrics,
        audit=audit,
        silver_validator=resolved_silver_validator,
        metadata_writer=resolved_metadata_writer,
        metadata_coordinator=metadata_coordinator,
        dq_calculator=resolved_dq_calculator,
        merge_resilience_policy=resolved_merge_resilience_policy,
    )
