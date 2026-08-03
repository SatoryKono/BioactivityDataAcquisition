"""Shared delegation helpers for DataSourcePort decorators."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.ports import DataSourcePort


@dataclass(frozen=True)
class DataSourceFetchRequest:
    """Immutable fetch call parameters shared by data source decorators."""

    entity_type: str
    limit: int | None = None
    query: str | None = None
    filter_ids: list[str] | None = None
    filter_field: str | None = None
    offset: int | None = None

    def as_kwargs(self) -> dict[str, object]:
        """Return keyword arguments accepted by DataSourcePort.fetch."""
        return {
            "entity_type": self.entity_type,
            "limit": self.limit,
            "query": self.query,
            "filter_ids": self.filter_ids,
            "filter_field": self.filter_field,
            "offset": self.offset,
        }


def delegated_provider_name(data_source: DataSourcePort) -> str:
    """Return the wrapped data source provider name using the public port."""
    return str(data_source.provider_name)


async def enter_delegated_data_source(data_source: DataSourcePort) -> None:
    """Enter the wrapped data source async context."""
    await data_source.__aenter__()


async def exit_delegated_data_source(
    data_source: DataSourcePort,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: TracebackType | None,
) -> None:
    """Exit the wrapped data source async context."""
    await data_source.__aexit__(exc_type, exc_val, exc_tb)


async def close_delegated_data_source(data_source: DataSourcePort) -> None:
    """Close the wrapped data source."""
    await data_source.aclose()


async def iter_delegated_fetch(
    data_source: DataSourcePort,
    request: DataSourceFetchRequest,
) -> AsyncIterator[JsonDict]:
    """Iterate a fetch request through the wrapped data source."""
    async for record in data_source.fetch(
        entity_type=request.entity_type,
        limit=request.limit,
        query=request.query,
        filter_ids=request.filter_ids,
        filter_field=request.filter_field,
        offset=request.offset,
    ):
        yield record
