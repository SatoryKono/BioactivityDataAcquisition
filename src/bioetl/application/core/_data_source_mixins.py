"""Shared generic mixins for application data source wrappers."""

from __future__ import annotations

__all__ = [
    "_FallbackFilterableTargetFetchMixin",
    "_FilterableTargetDelegationMixin",
    "_HasWrappedDataSource",
    "_SourceMetadataDelegationMixin",
    "_TargetEntityFetchDelegationMixin",
    "_WrappedDataSourceDelegationMixin",
    "_yield_plain_wrapped_fetch_records",
    "_yield_wrapped_fetch_records",
]

from typing import TYPE_CHECKING, Protocol, TypeVar, cast

from bioetl.application.core._target_data_source_fetch_support import (
    yield_plain_wrapped_fetch_records as _yield_plain_wrapped_fetch_records,
)
from bioetl.application.core._target_data_source_fetch_support import (
    yield_wrapped_fetch_records as _yield_wrapped_fetch_records,
)
from bioetl.application.core._target_data_source_mixins import (
    _FallbackFilterableTargetFetchMixin,
    _FilterableTargetDelegationMixin,
    _TargetEntityFetchDelegationMixin,
)

if TYPE_CHECKING:
    from types import TracebackType

    from bioetl.domain.ports import DataSourcePort, HealthCheckResult
    from bioetl.domain.types import HealthStatus

WrappedDataSourceT = TypeVar("WrappedDataSourceT", bound="_HasWrappedDataSource")


class _HasWrappedDataSource(Protocol):
    """Structural protocol for wrappers that delegate to a data source adapter."""

    _data_source: DataSourcePort

    def _after_wrapped_data_source_enter(self) -> None:
        """Reset wrapper-local state after entering the wrapped data source."""


class _SourceMetadataDelegationMixin:
    """Mixin for delegating get_source_metadata to wrapped data source."""

    def get_source_metadata(
        self: _HasWrappedDataSource, api_version: str | None = None
    ) -> object | None:
        """Delegate get_source_metadata to wrapped data source if supported."""
        get_metadata = getattr(self._data_source, "get_source_metadata", None)
        if get_metadata is not None and callable(get_metadata):
            return cast("object | None", get_metadata(api_version))
        return None


class _WrappedDataSourceDelegationMixin:
    """Common lifecycle and health delegation for wrapped data sources."""

    @property
    def provider_name(self: _HasWrappedDataSource) -> str:
        """Provider name from the wrapped data source."""
        provider_name: str = self._data_source.provider_name
        return provider_name

    async def __aenter__(self: WrappedDataSourceT) -> WrappedDataSourceT:
        """Enter async context and allow subclasses to reset wrapper state."""
        await self._data_source.__aenter__()
        self._after_wrapped_data_source_enter()
        return self

    def _after_wrapped_data_source_enter(self) -> None:
        """Hook for subclasses that need to reset state after adapter enter."""

    async def __aexit__(
        self: _HasWrappedDataSource,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Delegate async context teardown to the wrapped data source."""
        await self._data_source.__aexit__(exc_type, exc_val, exc_tb)

    async def health_check(self: _HasWrappedDataSource) -> HealthStatus:
        """Delegate health checks to the wrapped data source."""
        return await self._data_source.health_check()

    async def check_health(self: _HasWrappedDataSource) -> HealthCheckResult:
        """Delegate enhanced health checks when available, else synthesize one."""
        from bioetl.domain.ports import HealthCheckResult

        check_health = getattr(self._data_source, "check_health", None)
        if check_health is not None and callable(check_health):
            return await check_health()
        return HealthCheckResult(
            status=await self._data_source.health_check(),
            latency_ms=0.0,
            provider=self.provider_name,
        )

    async def aclose(self: _HasWrappedDataSource) -> None:
        """Delegate resource shutdown to the wrapped data source."""
        await self._data_source.aclose()
