"""Snapshot-backed data source for deterministic target protein classifications."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from types import TracebackType

from bioetl.application.services.protein_classification_resolution import (
    ProteinClassificationResolutionService,
)
from bioetl.domain.ports import DeltaReaderPort, LoggerPort
from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.infrastructure.adapters.chembl.protein_classification_graph import (
    ChEMBLProteinClassificationGraph,
)

from ._chembl_target_protein_classification_helpers import (
    _TARGET_PROTEIN_CLASSIFICATION_ENTITY_TYPE,
    build_target_component_indexes,
    resolve_target_ids,
)
from ._chembl_target_protein_classification_manifest import (
    source_manifest,
    with_source_manifest,
)

__all__ = ["TargetProteinClassificationSnapshotDataSource"]

_TARGET_TABLE = "chembl.target"
_TARGET_COMPONENT_TABLE = "chembl.target_component"
_PROTEIN_CLASS_TABLE = "chembl.protein_class"
class TargetProteinClassificationSnapshotDataSource:
    """Expose relation rows from materialized local ChEMBL snapshot tables."""

    provider_name = "chembl"

    def __init__(
        self,
        *,
        delta_reader: DeltaReaderPort,
        logger: LoggerPort,
        invalid_record_policy: str = "quarantine",
    ) -> None:
        self._delta_reader = delta_reader
        self._logger = logger
        self._invalid_record_policy = invalid_record_policy
        self._load_lock = asyncio.Lock()
        self._loaded = False
        self._target_component_ids: dict[str, tuple[int, ...]] = {}
        self._target_ids_by_component: dict[int, tuple[str, ...]] = {}
        self._resolution_service: ProteinClassificationResolutionService | None = None
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
        if entity_type != _TARGET_PROTEIN_CLASSIFICATION_ENTITY_TYPE:
            raise ValueError(
                "TargetProteinClassificationSnapshotDataSource only serves "
                f"{_TARGET_PROTEIN_CLASSIFICATION_ENTITY_TYPE}, got {entity_type}"
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
        target_ids = resolve_target_ids(
            filter_ids=filter_ids,
            filter_field=filter_field,
            target_component_ids=self._target_component_ids,
            target_ids_by_component=self._target_ids_by_component,
        )
        if offset is not None and offset > 0:
            target_ids = target_ids[offset:]

        emitted = 0
        for target_id in target_ids:
            for row in self._relation_rows_for_target(target_id):
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
        if entity_type != _TARGET_PROTEIN_CLASSIFICATION_ENTITY_TYPE:
            raise ValueError(
                "TargetProteinClassificationSnapshotDataSource only serves "
                f"{_TARGET_PROTEIN_CLASSIFICATION_ENTITY_TYPE}, got {entity_type}"
            )
        await self._ensure_loaded()
        target_id_sets = [
            set(
                resolve_target_ids(
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

    async def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        async with self._load_lock:
            if self._loaded:
                return
            target_rows = await self._read_rows(
                _TARGET_TABLE,
                columns=[
                    "target_id",
                    "component_ids",
                    "primary_component_id",
                    "target_components",
                ],
            )
            target_component_rows = await self._read_rows(
                _TARGET_COMPONENT_TABLE,
                columns=[
                    "component_id",
                    "protein_classification_ids",
                    "protein_classifications",
                ],
            )
            protein_class_rows = await self._read_rows(
                _PROTEIN_CLASS_TABLE,
                columns=[
                    "protein_class_id",
                    "parent_id",
                    "class_level",
                    "pref_name",
                    "protein_class_desc",
                    "replaced_by",
                ],
            )
            (
                self._target_component_ids,
                self._target_ids_by_component,
            ) = build_target_component_indexes(target_rows)
            self._source_manifest = source_manifest(
                target_rows=target_rows,
                target_component_rows=target_component_rows,
                protein_class_rows=protein_class_rows,
            )
            self._resolution_service = ProteinClassificationResolutionService(
                ChEMBLProteinClassificationGraph.from_rows(
                    protein_class_rows=protein_class_rows,
                    target_component_rows=target_component_rows,
                ),
                invalid_record_policy=self._invalid_record_policy,
            )
            self._loaded = True
            self._logger.info(
                "Loaded target protein classification snapshot inputs",
                target_count=len(self._target_component_ids),
                component_count=len(self._target_ids_by_component),
                source_tables=[
                    _TARGET_TABLE,
                    _TARGET_COMPONENT_TABLE,
                    _PROTEIN_CLASS_TABLE,
                ],
                source_snapshot_fingerprint=self._source_manifest.get(
                    "source_snapshot_fingerprint"
                ),
            )

    async def _read_rows(
        self,
        table_name: str,
        *,
        columns: list[str],
    ) -> list[JsonDict]:
        arrow_table = await self._delta_reader.read_table(table_name, columns=columns)
        return [dict(row) for row in arrow_table.to_pylist()]

    def _relation_rows_for_target(self, target_id: str) -> tuple[JsonDict, ...]:
        service = self._resolution_service
        if service is None:
            raise RuntimeError("Snapshot relation service was not initialized")
        component_ids = self._target_component_ids.get(target_id, ())
        result = service.resolve_target(
            target_id=target_id,
            component_ids=component_ids,
        )
        if result.dq_issues:
            self._logger.warning(
                "Target protein classification DQ issues detected",
                target_id=target_id,
                component_ids=list(component_ids),
                dq_issues=[
                    {
                        "component_id": issue.component_id,
                        "error_code": issue.error_code,
                        "message": issue.message,
                    }
                    for issue in result.dq_issues
                ],
                resolution_policy=self._invalid_record_policy,
        )
        return tuple(
            with_source_manifest(row.to_dict(), self._source_manifest)
            for row in result.rows
        )
