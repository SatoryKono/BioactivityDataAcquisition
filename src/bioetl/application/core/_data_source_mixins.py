"""Shared mixins for application data source wrappers."""

from __future__ import annotations

from typing import Any


class SourceMetadataDelegationMixin:
    """Mixin for delegating get_source_metadata to wrapped data source."""

    _data_source: Any

    def get_source_metadata(self, api_version: str | None = None) -> Any:
        """Delegate get_source_metadata to wrapped data source if supported."""
        get_metadata = getattr(self._data_source, "get_source_metadata", None)
        if get_metadata is not None and callable(get_metadata):
            return get_metadata(api_version)
        return None
