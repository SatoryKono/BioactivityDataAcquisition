"""Runtime services resolution for Gold writer."""

from __future__ import annotations

from typing import cast

from bioetl.domain.ports import (
    AuditPort,
    LineageStorePort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    MetricsPort,
    TracingPort,
)
from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
from bioetl.infrastructure.export.csv_exporter_contract import CsvExporterProtocol
from bioetl.infrastructure.storage.gold.runtime_helpers import (
    GoldWriterRuntimeServices,
    build_gold_writer_runtime_services,
)

__all__ = ["_resolve_runtime_services"]


def _resolve_runtime_services(
    *,
    runtime_services: GoldWriterRuntimeServices | None,
    legacy_kwargs: dict[str, object],
) -> GoldWriterRuntimeServices:
    """Normalize legacy constructor kwargs into grouped Gold runtime services."""
    csv_exporter = cast(
        "CsvExporterProtocol | None",
        legacy_kwargs.pop("csv_exporter", None),
    )
    tracing = cast(
        "TracingPort | None",
        legacy_kwargs.pop("tracing", None),
    )
    metrics = cast(
        "MetricsPort | None",
        legacy_kwargs.pop("metrics", None),
    )
    audit = cast(
        "AuditPort | None",
        legacy_kwargs.pop("audit", None),
    )
    metadata_writer = cast(
        "MetadataWriterPort | None",
        legacy_kwargs.pop("metadata_writer", None),
    )
    metadata_coordinator = cast(
        "MetadataCoordinatorPort | None",
        legacy_kwargs.pop("metadata_coordinator", None),
    )
    lineage_store = cast(
        "LineageStorePort | None",
        legacy_kwargs.pop("lineage_store", None),
    )
    contract_rollout_policy = cast(
        "ContractRolloutPolicy | None",
        legacy_kwargs.pop("contract_rollout_policy", None),
    )
    if legacy_kwargs:
        unexpected = ", ".join(sorted(legacy_kwargs))
        raise TypeError(f"Unexpected GoldWriter options: {unexpected}")

    return runtime_services or build_gold_writer_runtime_services(
        csv_exporter=csv_exporter,
        tracing=tracing,
        metrics=metrics,
        audit=audit,
        metadata_writer=metadata_writer,
        metadata_coordinator=metadata_coordinator,
        lineage_store=lineage_store,
        contract_rollout_policy=contract_rollout_policy,
    )
