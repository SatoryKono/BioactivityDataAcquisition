"""Runtime dependency resolution helpers for ``SilverWriter``."""

from __future__ import annotations

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
    from bioetl.domain.ports import MetadataWriterPort, SilverValidatorPort, TracingPort


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
