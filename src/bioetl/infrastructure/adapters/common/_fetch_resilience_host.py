"""Host contract for shared filtered batch recovery helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterable

    from bioetl.domain.ports import LoggerPort
else:
    AsyncIterator = object
    LoggerPort = object

__all__ = ["FilteredBatchRecoveryHost"]


class FilteredBatchRecoveryHost(Protocol):
    """Host contract for shared filtered batch recovery helpers."""

    _logger: LoggerPort
    provider_name: str

    def _is_retry_exhausted_error(self, error: Exception) -> bool: ...

    def _fetch_batch_with_reduction(
        self,
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        limit: int | None,
        seen_ids: set[str],
        pk_field: str,
        pk_fields: tuple[str, ...] | None = None,
    ) -> AsyncIterator[BronzeRecord]: ...

    def _yield_single_id_fallback(
        self,
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        seen_ids: set[str],
        pk_field: str,
        error: Exception,
        pk_fields: tuple[str, ...] | None = None,
    ) -> AsyncIterator[BronzeRecord]: ...

    def _batch_ids(
        self,
        filter_ids: list[str],
        *,
        batch_size: int,
    ) -> Iterable[list[str]]: ...

    def _get_api_pk_field(self, entity_type: str) -> str: ...

    def _get_api_dedup_fields(self, entity_type: str) -> tuple[str, ...]: ...

    def _yield_deduplicated_filtered_records(
        self,
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        limit: int | None,
        seen_ids: set[str],
        pk_field: str,
        pk_fields: tuple[str, ...] | None = None,
    ) -> AsyncIterator[BronzeRecord]: ...
