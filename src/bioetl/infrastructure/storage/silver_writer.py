# Host attrs/methods provided by concrete composition.
"""Silver layer writer (Delta Lake with merge/upsert)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, override

from deltalake import DeltaTable, write_deltalake

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.ports import (
    LoggerPort,
    TracingPort,
)
from bioetl.domain.types import BronzeRecord
from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
from bioetl.infrastructure.storage.base_delta_writer import (
    BaseDeltaWriter,
    _clear_delta_tables,
)
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
from bioetl.infrastructure.time import SystemClock

__all__ = ["SilverWriteMode", "SilverWriter", "_SilverWriteExecutionContext"]

# Keep Delta Lake dependency explicit in the root infrastructure adapter for
# medallion architecture guards; concrete calls live in split operation services.
_DELTA_LAKE_REQUIREMENTS = (DeltaTable, write_deltalake)


class SilverWriter(  # pyright: ignore[reportIncompatibleMethodOverride]
    SilverWriterRuntimeFacade,
    BaseDeltaWriter,
    SilverWriterMaintenanceMixin,
):
    """Writer for Silver layer (normalized data in Delta Lake)."""

    _tracing: TracingPort | None  # pyright: ignore[reportUninitializedInstanceVariable]
    _contract_rollout_policy: ContractRolloutPolicy | None  # pyright: ignore[reportUninitializedInstanceVariable]
    _host: object | None

    @override
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
    ) -> None:
        """Initialize Silver writer."""
        self._pipeline_name = pipeline_name

        if runtime_request is None:
            runtime_request = SilverWriterRuntimeServicesRequest(
                logger=logger,
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
        self._clock = SystemClock()
        self._transform_version = transform_version
        self._transform_steps = transform_steps or ()
        self._host = self

    @override
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
    @override
    def _enforce_write_policy(self, mode: SilverWriteMode, table_name: str) -> None:
        super()._enforce_write_policy(mode, table_name)

    @override
    def _validate_silver_pandera(
        self,
        records: list[BronzeRecord],
        table_name: str,
    ) -> None:
        super()._validate_silver_pandera(records, table_name)

    async def _check_schema_drift(
        self,
        table_name: str,
        records: list[BronzeRecord],
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
    ) -> None:
        await super()._check_schema_drift(table_name, records, on_schema_mismatch)

    async def clear_silver(self, table_name: str, dry_run: bool = False) -> int:
        """Implement ``SilverStoragePort`` clear for rebuild/backfill paths."""
        import asyncio

        return await asyncio.to_thread(
            _clear_delta_tables,
            base_path=Path(str(self.base_path)),
            table_path=Path(self._resolve_table_path(table_name)),
            dry_run=dry_run,
        )
