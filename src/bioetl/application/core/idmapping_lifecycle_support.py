"""Lifecycle helpers for IDMappingDataSource."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        IDMappingPort,
        IDMappingSourceReaderPort,
        LoggerPort,
    )


class _IDMappingLifecycleState(Protocol):
    """Structural contract for IDMappingDataSource lifecycle helpers."""
    _client: IDMappingPort
    _id_source_reader: IDMappingSourceReaderPort
    _input_path: str
    _logger: LoggerPort
    _seed_ids: list[str] | None
    _is_open: bool


async def enter_data_source(state: _IDMappingLifecycleState) -> None:
    """Enter the underlying mapping client context."""
    await state._client.__aenter__()
    state._is_open = True


async def close_data_source(state: _IDMappingLifecycleState) -> None:
    """Close the underlying mapping client when open."""
    if state._is_open:
        await state._client.__aexit__(None, None, None)
    state._is_open = False


async def health_check(state: _IDMappingLifecycleState) -> HealthStatus:
    """Validate local input readiness and downstream API health."""
    if not state._seed_ids:
        file_exists = await state._id_source_reader.source_exists(
            source_path=state._input_path
        )
        if not file_exists:
            state._logger.warning(
                "health_check_failed",
                reason="input_file_missing",
                path=state._input_path,
            )
            return HealthStatus.UNHEALTHY
    api_status = await state._client.health_check()
    if api_status != HealthStatus.HEALTHY:
        return api_status
    return HealthStatus.HEALTHY
