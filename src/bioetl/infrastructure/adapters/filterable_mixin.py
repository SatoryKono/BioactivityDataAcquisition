# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Mixin providing default stub implementations for FilterableDataSourcePort.

Reduces code duplication where:
- fetch_multi_filtered is not supported by the provider API
- fetch_filtered_with_fallback should just delegate to fetch_filtered

Classes with real implementations (OpenAlex, SemanticScholar, CrossRef, UniProt)
should override these methods instead of using the mixin.

Note: This is a mixin module, not a standalone class. Health checks are provided
by the base classes (BaseHttpAdapter via HealthCheckProviderMixin).
"""

from __future__ import annotations

__all__ = [
    "DelegatingFallbackMixin",
    "FetchFilteredProtocol",
    "FilterableStubMixin",
    "NotSupportedMultiFilterMixin",
    "iter_filtered_records_with_default_field",
    "raising_async_iterator",
]


from typing import Any, cast, TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class _RaisingAsyncIterator:
    """Async iterator that raises a provided exception when consumed."""

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    def __aiter__(self) -> _RaisingAsyncIterator:
        return self

    async def __anext__(self) -> JsonDict:
        raise self._exc


def raising_async_iterator(exc: BaseException) -> AsyncIterator[JsonDict]:
    """Return an async iterator that raises ``exc`` on first iteration."""
    return _RaisingAsyncIterator(exc)


@runtime_checkable
class FetchFilteredProtocol(Protocol):
    """Protocol for adapters that implement fetch_filtered method."""

    def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[
        JsonDict  # Any: filter record values vary (str|int|float|list)
    ]:  # Any: filter record values vary (str|int|float|list)
        """Fetch records filtered by specific IDs.

        Args:
            entity_type: Entity type identifier.
            filter_ids: List of identifiers to filter by.
            filter_field: Field name to apply filter on.
            limit: Maximum number of records to process.

        Returns:
            Async iterator yielding fetched records.
        """
        ...


class NotSupportedMultiFilterMixin:
    """Mixin providing stub fetch_multi_filtered for unsupported adapters.

    Use this mixin for adapters where multi-field filtering is not supported
    by the provider API. The method raises NotImplementedError with a
    descriptive message including the provider name.

    Requirements:
        - Class must have a `provider_name` attribute (str)
        - Class may define `unsupported_multi_filter_message` to preserve a
          provider-specific error message.

    Example:
        >>> class PubChemAdapter(NotSupportedMultiFilterMixin, BaseHttpAdapter):
        ...     provider_name = "pubchem"
        ...     # fetch_multi_filtered is now provided by mixin
    """

    provider_name: str = cast(Any, None)  # Any: host attr default (PD3) Must be defined by the adapter class
    unsupported_multi_filter_message: ClassVar[str | None] = None

    def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[
        JsonDict  # Any: filter record values vary (str|int|float|list)
    ]:  # Any: filter record values vary (str|int|float|list)
        """Multi-field filtering not supported - raises NotImplementedError.

        Args:
            entity_type: Type of entity to fetch (unused).
            filters: Dictionary of field names to ID lists (unused).
            limit: Maximum number of records (unused).

        Raises:
            NotImplementedError: Always, as the provider doesn't support
                multi-field filtering.

        Returns:
            Async iterator yielding fetched records.
        """
        # Mark unused parameters
        del entity_type, filters, limit

        message = self.unsupported_multi_filter_message or (
            f"{self.provider_name} does not support multi-field filtering. "
            "Use fetch_filtered() with a single filter_field instead."
        )
        return raising_async_iterator(NotImplementedError(message))


async def iter_filtered_records_with_default_field(
    adapter: FetchFilteredProtocol,
    *,
    entity_type: str,
    filter_ids: list[str],
    filter_field: str | None,
    default_filter_field: str,
    limit: int | None,
) -> AsyncIterator[JsonDict]:
    """Delegate filtered fetch after resolving a provider default field."""
    effective_filter_field = filter_field or default_filter_field
    async for record in adapter.fetch_filtered(
        entity_type=entity_type,
        filter_ids=filter_ids,
        filter_field=effective_filter_field,
        limit=limit,
    ):
        yield record


class DelegatingFallbackMixin:
    """Mixin providing fetch_filtered_with_fallback that delegates to fetch_filtered.

    Use this mixin for adapters where fallback search is not needed because
    the primary IDs are always resolvable (e.g., CID for PubChem, PMID for PubMed).

    Requirements:
        - Class must implement fetch_filtered() method

    Example:
        >>> class PubMedAdapter(DelegatingFallbackMixin, BaseHttpAdapter):
        ...     async def fetch_filtered(self, entity_type, filter_ids, ...):
        ...         ...
        ...     # fetch_filtered_with_fallback is now provided by mixin
    """

    async def fetch_filtered_with_fallback(
        self: FetchFilteredProtocol,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[
        JsonDict  # Any: filter record values vary (str|int|float|list)
    ]:  # Any: filter record values vary (str|int|float|list)
        """Fallback not needed - delegates to fetch_filtered().

        The fallback_mapping parameter is ignored since the primary IDs
        are always resolvable for this provider.

        Args:
            entity_type: Type of entity to fetch.
            filter_ids: List of IDs to filter by.
            filter_field: Field name to filter on.
            fallback_mapping: Ignored - primary IDs are always resolvable.
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records matching the filter criteria.

        Returns:
            Async iterator yielding fetched records.
        """
        del fallback_mapping  # Unused - primary IDs are always resolvable
        async for record in self.fetch_filtered(
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=limit,
        ):
            yield record


class FilterableStubMixin(NotSupportedMultiFilterMixin, DelegatingFallbackMixin):
    """Combined mixin for adapters that need both stub implementations.

    Provides:
    - fetch_multi_filtered: raises NotImplementedError
    - fetch_filtered_with_fallback: delegates to fetch_filtered

    Use this for adapters where:
    1. Multi-field filtering is not supported
    2. Primary IDs are always resolvable (no fallback needed)

    Requirements:
        - Class must have a `provider_name` attribute (str)
        - Class must implement fetch_filtered() method

    Example:
        >>> class PubChemAdapter(FilterableStubMixin, BaseHttpAdapter):
        ...     provider_name = "pubchem"
        ...     async def fetch_filtered(self, entity_type, filter_ids, ...):
        ...         ...
    """
