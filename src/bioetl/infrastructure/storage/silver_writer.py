"""Silver layer writer (Delta Lake with merge/upsert)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from deltalake import DeltaTable, write_deltalake

from bioetl.domain.behavior.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.medallion import SilverWriteMode, WriteModePolicy
from bioetl.domain.ports import (
    AuditPort,
    LineageStorePort,
    LoggerPort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    MetricsPort,
    SilverValidatorPort,
    TracingPort,
)
from bioetl.infrastructure.export.csv_exporter_contract import CsvExporterProtocol
from bioetl.infrastructure.storage.base_delta_writer import BaseDeltaWriter
from bioetl.infrastructure.storage.delta.resilience import SilverMergeResiliencePolicy
from bioetl.infrastructure.storage.silver.maintenance_mixin import (
    SilverWriterMaintenanceMixin,
)
from bioetl.infrastructure.storage.silver.pipeline_helpers import (
    _SilverWriteExecutionContext,
)
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServices,
    SilverWriterRuntimeServicesRequest,
)
from bioetl.infrastructure.storage.silver.writer_runtime_facade import (
    SilverWriterRuntimeFacade,
)
from bioetl.infrastructure.storage.silver.writer_runtime_support import (
    _assign_runtime_services,
    _resolve_runtime_services_for_writer,
    _rewire_runtime_services,
)

__all__ = ["SilverWriteMode", "SilverWriter", "_SilverWriteExecutionContext"]

# Keep Delta Lake dependency explicit in the root infrastructure adapter for
# medallion architecture guards; concrete calls live in split operation services.
_DELTA_LAKE_REQUIREMENTS = (DeltaTable, write_deltalake)


class SilverWriter(
    SilverWriterRuntimeFacade,
    BaseDeltaWriter,
    SilverWriterMaintenanceMixin,
):
    """Writer for Silver layer (normalized data in Delta Lake)."""

    _tracing: TracingPort | None
    _contract_rollout_policy: object | None
    _maintenance: object | None
    _metadata: object | None
    _validation: object | None
    _delta: object | None
    _arrow: object | None
    _merged: object | None
    _postwrite: object | None
    _host: object | None

    def __setattr__(self, name: str, value: object) -> None:
        """Keep validation service host wiring in sync for direct test assignment."""
        object.__setattr__(self, name, value)
        if name == "_validation" and value is not None and hasattr(value, "_host"):
            object.__setattr__(value, "_host", self)

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
        runtime_services: SilverWriterRuntimeServices | None = None,
        flat_structure: bool = False,
        pipeline_name: str | None = None,
        runtime_request: SilverWriterRuntimeServicesRequest | None = None,
        csv_exporter: CsvExporterProtocol | None = None,
        tracing: TracingPort | None = None,
        write_policy: WriteModePolicy | None = None,
        metrics: MetricsPort | None = None,
        audit: AuditPort | None = None,
        silver_validator: SilverValidatorPort | None = None,
        metadata_writer: MetadataWriterPort | None = None,
        metadata_coordinator: MetadataCoordinatorPort | None = None,
        lineage_store: LineageStorePort | None = None,
        dq_calculator: DQMetricsCalculator | None = None,
        merge_resilience_policy: SilverMergeResiliencePolicy | None = None,
        contract_rollout_policy: Any = None,  # Any: Dynamic policy object with .mode and .write_versions attributes
    ) -> None:
        """Initialize Silver writer."""
        self._pipeline_name = pipeline_name

        explicit_runtime_dependencies = {
            "csv_exporter": csv_exporter,
            "tracing": tracing,
            "write_policy": write_policy,
            "metrics": metrics,
            "audit": audit,
            "silver_validator": silver_validator,
            "metadata_writer": metadata_writer,
            "metadata_coordinator": metadata_coordinator,
            "lineage_store": lineage_store,
            "dq_calculator": dq_calculator,
            "merge_resilience_policy": merge_resilience_policy,
            "contract_rollout_policy": contract_rollout_policy,
        }
        conflicting_dependencies = sorted(
            name for name, value in explicit_runtime_dependencies.items() if value is not None
        )
        if runtime_request is not None and conflicting_dependencies:
            raise TypeError(
                "Cannot pass direct runtime dependency kwargs when "
                f"'runtime_request' is provided: {', '.join(conflicting_dependencies)}"
            )

        if runtime_request is None:
            runtime_request = SilverWriterRuntimeServicesRequest(
                csv_exporter=csv_exporter,
                tracing=tracing,
                write_policy=write_policy,
                metrics=metrics,
                audit=audit,
                logger=logger,
                silver_validator=silver_validator,
                metadata_writer=metadata_writer,
                metadata_coordinator=metadata_coordinator,
                lineage_store=lineage_store,
                dq_calculator=dq_calculator,
                merge_resilience_policy=merge_resilience_policy,
                contract_rollout_policy=contract_rollout_policy,
            )

        super().__init__(base_path, logger, flat_structure=flat_structure)
        services = _resolve_runtime_services_for_writer(
            writer=self,
            base_path=base_path,
            runtime_services=runtime_services,
            runtime_request=runtime_request,
        )
        _assign_runtime_services(self, services)
        _rewire_runtime_services(self)
        self._transform_version = transform_version
        self._transform_steps = transform_steps or ()
        self._host = self

    def _should_dual_write(self) -> bool:
        """Return True when rollout policy requires Silver shadow writes."""
        if self._contract_rollout_policy is None:
            return False
        return (
            self._contract_rollout_policy.mode in {"dual_write", "dual_read_write"}
            and len(self._contract_rollout_policy.write_versions) > 1
        )

    # Keep legacy validation method names on the root adapter for architecture
    # guards and direct patch coverage, while runtime services own the work.
    def _enforce_write_policy(self, mode: SilverWriteMode, table_name: str) -> None:
        super()._enforce_write_policy(mode, table_name)

    def _validate_silver_pandera(
        self,
        records: list[object],
        table_name: str,
    ) -> None:
        super()._validate_silver_pandera(records, table_name)

    async def _check_schema_drift(
        self,
        table_name: str,
        records: list[object],
        on_schema_mismatch: str,
    ) -> None:
        await super()._check_schema_drift(table_name, records, on_schema_mismatch)
