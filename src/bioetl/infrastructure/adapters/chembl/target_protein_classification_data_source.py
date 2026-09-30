"""Snapshot-backed data source for deterministic target protein classifications."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from types import TracebackType
from typing import TYPE_CHECKING

from bioetl.domain.ports import DeltaReaderPort, LoggerPort
from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.infrastructure.adapters.chembl.target_protein_classification_loading_mixin import (
    _PROTEIN_CLASS_TABLE,
    _TARGET_COMPONENT_TABLE,
    _TARGET_TABLE,
    IndexBuilder,
    TargetIdResolver,
    TargetProteinClassificationLoadingMixin,
    _ResolutionService,
)

if TYPE_CHECKING:
    from bioetl.domain.mapping.protein_class_target_type import (
        ProteinClassTargetTypeMappingData,
    )

__all__ = ["TargetProteinClassificationSnapshotDataSource"]


class TargetProteinClassificationSnapshotDataSource(
    TargetProteinClassificationLoadingMixin
):
    """Expose relation rows from materialized local ChEMBL snapshot tables.

    Implements FilterableDataSourcePort via fetch_filtered.
    """

    provider_name = "chembl"

    def __init__(
        self,
        *,
        delta_reader: DeltaReaderPort,
        logger: LoggerPort,
        invalid_record_policy: str = "quarantine",
        target_type_mapping_data: ProteinClassTargetTypeMappingData | None = None,
        resolution_factory: Callable[..., object] | None = None,
        entity_type: str,
        index_builder: IndexBuilder,
        target_id_resolver: TargetIdResolver,
    ) -> None:
        self._delta_reader = delta_reader
        self._logger = logger
        self._invalid_record_policy = invalid_record_policy
        self._target_type_mapping_data = target_type_mapping_data
        self._resolution_factory = resolution_factory
        self._entity_type = entity_type
        self._index_builder = index_builder
        self._target_id_resolver = target_id_resolver
        self._load_lock = asyncio.Lock()
        self._loaded = False
        self._target_component_ids: dict[str, tuple[int, ...]] = {}
        self._target_ids_by_component: dict[int, tuple[str, ...]] = {}
        self._resolution_service: _ResolutionService | None = None
        self._source_manifest: JsonDict = {}

    async def __aenter__(self) -> TargetProteinClassificationSnapshotDataSource:
        await self._ensure_loaded()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._delta_reader.aclose()

    async def health_check(self) -> HealthStatus:
        required_tables = (
            _TARGET_TABLE,
            _TARGET_COMPONENT_TABLE,
            _PROTEIN_CLASS_TABLE,
        )
        table_states = {
            table_name: await self._delta_reader.table_exists(table_name)
            for table_name in required_tables
        }
        if all(table_states.values()):
            return HealthStatus.HEALTHY
        self._logger.warning(
            "Target protein classification snapshot tables missing",
            table_states=table_states,
        )
        return HealthStatus.DEGRADED

    def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        if entity_type != self._entity_type:
            raise ValueError(
                "TargetProteinClassificationSnapshotDataSource only serves "
                f"{self._entity_type}, got {entity_type}"
            )
        return self._iter_relation_rows(
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
            offset=offset,
        )

    def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        return self.fetch(
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=limit,
        )

    def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        return self._iter_multi_filtered_relation_rows(
            entity_type=entity_type,
            filters=filters,
            limit=limit,
        )

    async def _iter_relation_rows(
        self,
        *,
        limit: int | None,
        query: str | None,
        filter_ids: list[str] | None,
        filter_field: str | None,
        offset: int | None,
    ) -> AsyncIterator[JsonDict]:
        del query
        await self._ensure_loaded()
        target_ids = self._target_id_resolver(
            filter_ids=filter_ids,
            filter_field=filter_field,
            target_component_ids=self._target_component_ids,
            target_ids_by_component=self._target_ids_by_component,
        )
        emitted = 0
        skipped = 0
        row_offset = 0 if offset is None or offset < 0 else offset
        for target_id in target_ids:
            for row in self._relation_rows_for_target(target_id):
                if skipped < row_offset:
                    skipped += 1
                    continue
                yield row
                emitted += 1
                if limit is not None and emitted >= limit:
                    return

    async def _iter_multi_filtered_relation_rows(
        self,
        *,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        if entity_type != self._entity_type:
            raise ValueError(
                "TargetProteinClassificationSnapshotDataSource only serves "
                f"{self._entity_type}, got {entity_type}"
            )
        await self._ensure_loaded()
        target_id_sets = [
            set(
                self._target_id_resolver(
                    filter_ids=filter_ids,
                    filter_field=filter_field,
                    target_component_ids=self._target_component_ids,
                    target_ids_by_component=self._target_ids_by_component,
                )
            )
            for filter_field, filter_ids in filters.items()
        ]
        filtered_target_ids = (
            tuple(sorted(set.intersection(*target_id_sets))) if target_id_sets else ()
        )
        emitted = 0
        for target_id in filtered_target_ids:
            for row in self._relation_rows_for_target(target_id):
                yield row
                emitted += 1
                if limit is not None and emitted >= limit:
                    return
