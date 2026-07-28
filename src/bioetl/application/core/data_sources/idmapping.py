"""ID Mapping Data Source.

Implements DataSourcePort for ChEMBL → UniProt ID mapping pipeline.
Loads ChEMBL target IDs via a reader port and maps them to UniProt accessions.
"""

from __future__ import annotations

__all__ = ["IDMappingDataSource"]

from typing import TYPE_CHECKING, Self

from bioetl.application.core import idmapping_fetch_support as fetch_support
from bioetl.application.core import idmapping_lifecycle_support as lifecycle_support
from bioetl.domain.types import HealthStatus, JsonDict

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from types import TracebackType

    from bioetl.domain.ports import (
        IDMappingPort,
        IDMappingSourceReaderPort,
        LoggerPort,
    )

class IDMappingDataSource:
    """Data source for ChEMBL → UniProt ID mapping."""

    provider_name: str = "uniprot_idmapping"

    def __init__(
        self,
        idmapping_client: IDMappingPort,
        id_source_reader: IDMappingSourceReaderPort,
        input_path: str,
        logger: LoggerPort,
        from_db: str = "ChEMBL",
        to_db: str = "UniProtKB",
        id_column: str = "target_id",
        seed_ids: list[str] | None = None,
    ) -> None:
        self._client = idmapping_client
        self._id_source_reader = id_source_reader
        self._input_path = str(input_path)
        self._logger = logger
        self._from_db = from_db
        self._to_db = to_db
        self._id_column = id_column
        self._seed_ids = seed_ids
        self._is_open = False

    async def __aenter__(self) -> Self:
        await lifecycle_support.enter_data_source(self)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await lifecycle_support.close_data_source(self)

    def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        return fetch_support.fetch_records(
            self, entity_type, limit, query, filter_ids, filter_field, offset
        )

    async def health_check(self) -> HealthStatus:
        return await lifecycle_support.health_check(self)

    def __repr__(self) -> str:
        return fetch_support.format_repr(self)
