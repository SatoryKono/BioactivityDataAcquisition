# pyright: reportUninitializedInstanceVariable=false
# pyright: reportAttributeAccessIssue=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Context, DQ, and persistence facade methods for Silver metadata services."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from bioetl.domain.behavior.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.ports import (
    AuditPort,
    LineageStorePort,
    LoggerPort,
    MetadataCoordinatorPort,
    MetricsPort,
)
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.infrastructure.storage.silver.operations.metadata_dq_operations import (
    compute_silver_dq_metrics_operation,
    get_flat_structure,
    get_transform_steps,
    get_transform_version,
    persist_silver_metadata_operation,
    resolve_finalization_dq_metrics_operation,
    resolve_silver_manifest_id,
    resolve_version_after_operation,
    should_skip_silver_metadata_write_operation,
    write_silver_metadata_file_operation,
)

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.domain.value_objects.silver_result import SilverWriteResult

__all__ = ["_SilverMetadataContextFacade"]


class _SilverMetadataContextFacade:
    """Context, DQ, and sidecar-persistence methods for metadata services."""

    _logger: LoggerPort
    _metrics: MetricsPort | None
    _audit: AuditPort | None
    _metadata_writer: object | None
    _metadata_coordinator: MetadataCoordinatorPort | None
    _lineage_store: LineageStorePort | None
    _dq_calculator: DQMetricsCalculator | None
    _host: object | None

    @property
    def _flat_structure(self) -> bool:
        """Resolve flat-structure metadata mode from the current host, if any."""
        return get_flat_structure(self)

    @property
    def _transform_version(self) -> str | None:
        """Resolve transform version from the current host, if any."""
        return get_transform_version(self)

    @property
    def _transform_steps(self) -> tuple[str, ...]:
        """Resolve transform steps from the current host with a stable fallback."""
        return get_transform_steps(self)

    def _resolve_manifest_id(self, *, records: list[BronzeRecord]) -> str | None:
        """Resolve control-plane manifest id from records, host, or coordinator."""
        return resolve_silver_manifest_id(self, records=records)

    async def _persist_silver_metadata(
        self,
        *,
        metadata: SilverMetadata,
        table_name: str,
        table_path: str,
    ) -> SilverWriteResult | None:
        """Persist metadata using whichever writer signature is available."""
        return await persist_silver_metadata_operation(
            self,
            metadata=metadata,
            table_name=table_name,
            table_path=table_path,
        )

    async def _resolve_finalization_dq_metrics(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        quarantined_count: int | None = None,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics:
        """Resolve DQ metrics via host override when present, otherwise compute them."""
        return await resolve_finalization_dq_metrics_operation(
            self,
            table_name=table_name,
            records=records,
            quarantined_count=quarantined_count,
            validation_errors=validation_errors,
        )

    async def _resolve_version_after(self, table_path: str) -> int | None:
        """Read Delta version via host helper when available."""
        return await resolve_version_after_operation(self, table_path)

    async def _get_delta_version(self, table_path: str) -> int | None:
        """Compatibility hook expected by canonical metadata helpers."""
        return await self._resolve_version_after(table_path)

    async def _compute_dq_metrics(
        self,
        table_name: str,
        records: list[BronzeRecord],
        quarantined_count: int = 0,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics:
        """Compatibility hook expected by canonical finalization helpers."""
        return await self._resolve_finalization_dq_metrics(
            table_name=table_name,
            records=records,
            quarantined_count=quarantined_count,
            validation_errors=validation_errors,
        )

    async def compute_dq_metrics(
        self,
        arrow_data: pa.Table,
        *,
        quarantined_count: int | None = None,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics:
        """Compute data quality metrics for Silver write."""
        return await compute_silver_dq_metrics_operation(
            self,
            arrow_data,
            quarantined_count=quarantined_count,
            validation_errors=validation_errors,
        )

    def _should_skip_silver_metadata_write(
        self,
        *,
        records: list[BronzeRecord],
        table_path: str,
        event_name: str,
    ) -> bool:
        """Return whether canonical Silver metadata publication should short-circuit."""
        return should_skip_silver_metadata_write_operation(
            self,
            records=records,
            table_path=table_path,
            event_name=event_name,
        )

    async def _write_silver_metadata_file(
        self,
        *,
        table_path: str,
        metadata: SilverMetadata,
        table_name: str,
        provider_name: str,
        entity_name: str,
    ) -> None:
        """Persist one canonical Silver metadata sidecar through the writer port."""
        await write_silver_metadata_file_operation(
            self,
            table_path=table_path,
            metadata=metadata,
            table_name=table_name,
            provider_name=provider_name,
            entity_name=entity_name,
        )
