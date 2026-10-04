# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Snapshot-loading mixin for target protein classification data sources."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Protocol, cast

import pyarrow as pa

from bioetl.domain.exceptions.internal_state import InvalidStateError
from bioetl.domain.ports import DeltaReaderPort, LoggerPort
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.chembl.protein_classification_source_manifest import (
    source_manifest,
    with_source_manifest,
)

__all__ = [
    "_PROTEIN_CLASS_TABLE",
    "_TARGET_COMPONENT_TABLE",
    "_TARGET_TABLE",
    "IndexBuilder",
    "TargetIdResolver",
    "TargetProteinClassificationLoadingMixin",
]

_TARGET_TABLE = "chembl.target"
_TARGET_COMPONENT_TABLE = "chembl.target_component"
_PROTEIN_CLASS_TABLE = "chembl.protein_class"


class _ResolutionRow(Protocol):
    def to_dict(self) -> JsonDict: ...


class _ResolutionIssue(Protocol):
    @property
    def component_id(self) -> int | None: ...

    @property
    def error_code(self) -> str: ...

    @property
    def message(self) -> str: ...


class _ResolutionResult(Protocol):
    @property
    def rows(self) -> Sequence[_ResolutionRow]: ...

    @property
    def dq_issues(self) -> Sequence[_ResolutionIssue]: ...


class _ResolutionService(Protocol):
    def resolve_target(
        self,
        *,
        target_id: str,
        component_ids: tuple[int, ...],
    ) -> _ResolutionResult: ...


IndexBuilder = Callable[
    [Iterable[Mapping[str, object]]],
    tuple[dict[str, tuple[int, ...]], dict[int, tuple[str, ...]]],
]
TargetIdResolver = Callable[..., tuple[str, ...]]


class TargetProteinClassificationLoadingMixin:
    """Load and serve materialized ChEMBL snapshot tables.

    Host class provides ``_delta_reader``, ``_logger``, ``_load_lock``,
    ``_loaded``, ``_target_component_ids``, ``_target_ids_by_component``,
    ``_resolution_service``, ``_resolution_factory``, ``_source_manifest``,
    ``_index_builder``, ``_invalid_record_policy``, and
    ``_target_type_mapping_data``.
    """

    _delta_reader: DeltaReaderPort
    _logger: LoggerPort
    _load_lock: asyncio.Lock
    _loaded: bool
    _target_component_ids: dict[str, tuple[int, ...]]
    _target_ids_by_component: dict[int, tuple[str, ...]]
    _resolution_service: _ResolutionService | None
    _resolution_factory: Callable[..., object] | None
    _source_manifest: JsonDict
    _index_builder: IndexBuilder
    _invalid_record_policy: str
    _target_type_mapping_data: object | None

    def _is_loaded(self) -> bool:
        """Return whether the reference rows are already loaded."""
        return self._loaded

    async def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        async with self._load_lock:
            # Re-read via helper: the outer fast-path check narrows
            # self._loaded for mypy, but another coroutine may have loaded
            # while awaiting the lock.
            if self._is_loaded():
                return
            missing = [
                table
                for table in (
                    _TARGET_TABLE,
                    _TARGET_COMPONENT_TABLE,
                    _PROTEIN_CLASS_TABLE,
                )
                if not await self._delta_reader.table_exists(table)
            ]
            if missing:
                raise InvalidStateError(
                    "blocked_dependency: missing Gold snapshot(s): "
                    + ", ".join(missing)
                    + ". Materialize and validate the upstream tables before retrying; "
                    "an absent table is not a validated empty result.",
                    current_state="blocked_dependency",
                    attempted_operation="load_target_protein_classification_snapshots",
                )
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
            ) = self._index_builder(target_rows)
            self._source_manifest = source_manifest(
                target_rows=target_rows,
                target_component_rows=target_component_rows,
                protein_class_rows=protein_class_rows,
            )
            factory = self._resolution_factory
            if factory is None:
                raise RuntimeError(
                    "Target protein classification resolution factory was not injected"
                )
            self._resolution_service = cast(
                "_ResolutionService",
                factory(
                    protein_class_rows=protein_class_rows,
                    target_component_rows=target_component_rows,
                    invalid_record_policy=self._invalid_record_policy,
                    target_type_mapping_data=self._target_type_mapping_data,
                ),
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
        arrow_table = cast("pa.Table", arrow_table)
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
