"""Silver layer writer (Delta Lake with merge/upsert)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, cast

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
from bioetl.domain.types import BronzeRecord
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
        **runtime_dependencies: object,
    ) -> None:
        """Initialize Silver writer."""
        self._pipeline_name = pipeline_name

        if runtime_request is not None and runtime_dependencies:
            unexpected_dependency = ", ".join(sorted(runtime_dependencies))
            raise TypeError(
                "Cannot pass legacy runtime dependency kwargs when "
                f"'runtime_request' is provided: {unexpected_dependency}"
            )

        if runtime_request is None:
            runtime_request = SilverWriterRuntimeServicesRequest(
                csv_exporter=cast(
                    CsvExporterProtocol | None,
                    runtime_dependencies.pop("csv_exporter", None),
                ),
                tracing=cast(
                    TracingPort | None,
                    runtime_dependencies.pop("tracing", None),
                ),
                write_policy=cast(
                    WriteModePolicy | None,
                    runtime_dependencies.pop("write_policy", None),
                ),
                metrics=cast(
                    MetricsPort | None, runtime_dependencies.pop("metrics", None)
                ),
                audit=cast(AuditPort | None, runtime_dependencies.pop("audit", None)),
                logger=cast(
                    LoggerPort | None, runtime_dependencies.pop("logger", None)
                ),
                silver_validator=cast(
                    SilverValidatorPort | None,
                    runtime_dependencies.pop("silver_validator", None),
                ),
                metadata_writer=cast(
                    MetadataWriterPort | None,
                    runtime_dependencies.pop("metadata_writer", None),
                ),
                metadata_coordinator=cast(
                    MetadataCoordinatorPort | None,
                    runtime_dependencies.pop("metadata_coordinator", None),
                ),
                lineage_store=cast(
                    LineageStorePort | None,
                    runtime_dependencies.pop("lineage_store", None),
                ),
                dq_calculator=cast(
                    DQMetricsCalculator | None,
                    runtime_dependencies.pop("dq_calculator", None),
                ),
                merge_resilience_policy=cast(
                    SilverMergeResiliencePolicy | None,
                    runtime_dependencies.pop("merge_resilience_policy", None),
                ),
                contract_rollout_policy=cast(
                    Any,
                    runtime_dependencies.pop("contract_rollout_policy", None),
                ),
            )
            if runtime_dependencies:
                unexpected_dependency = ", ".join(sorted(runtime_dependencies))
                raise TypeError(
                    "Unexpected legacy runtime dependency kwargs: "
                    f"{unexpected_dependency}"
                )
        else:
            runtime_request = cast(SilverWriterRuntimeServicesRequest, runtime_request)

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

    def _enforce_write_policy(
        self,
        mode: SilverWriteMode,
        table_name: str,
    ) -> None:
        """Delegate Silver write policy enforcement to the runtime facade."""
        super()._enforce_write_policy(mode, table_name)

    def _validate_silver_pandera(
        self,
        records: list[BronzeRecord],
        table_name: str,
    ) -> None:
        """Delegate Pandera validation to the runtime facade."""
        super()._validate_silver_pandera(records, table_name)

    async def _check_schema_drift(
        self,
        table_name: str,
        records: list[BronzeRecord],
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
    ) -> None:
        """Delegate schema drift validation to the runtime facade."""
        await super()._check_schema_drift(
            table_name,
            records,
            on_schema_mismatch,
        )
