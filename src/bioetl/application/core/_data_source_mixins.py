"""Shared mixins for application data source wrappers."""

from __future__ import annotations

from typing import Any, Protocol


class _HasWrappedDataSource(Protocol):
    """Structural protocol for application classes that wrap a data source adapter.

    Used as a self-type constraint in mixin methods that need to access
    the wrapped ``_data_source`` attribute without inheriting from a concrete class.
    Conforms to the Ports and Adapters pattern (Hexagonal Architecture) where the
    application layer delegates to an injected infrastructure adapter.

    Attributes:
        _data_source: The wrapped data source adapter instance.
    """

    _data_source: object


class _SourceMetadataDelegationMixin:
    """Mixin for delegating get_source_metadata to wrapped data source."""

    def get_source_metadata(
        self: _HasWrappedDataSource, api_version: str | None = None
    ) -> Any:  # Any: SourceMetadata type varies per adapter implementation
        """Delegate get_source_metadata to wrapped data source if supported.

        Args:
            api_version: Api version.

        Returns:
            Source metadata.
        """
        get_metadata = getattr(self._data_source, "get_source_metadata", None)
        if get_metadata is not None and callable(get_metadata):
            return get_metadata(api_version)
        return None
