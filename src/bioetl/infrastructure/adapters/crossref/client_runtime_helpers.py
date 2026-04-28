"""Runtime validation helpers for the CrossRef adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.infrastructure.adapters.common import ComposableFallbackDecorator
from bioetl.infrastructure.adapters.crossref.client_builders import (
    _create_default_crossref_fetch_flow,
)
from bioetl.infrastructure.adapters.crossref.fallback import (
    CrossRefTitleFallbackHandler,
)
from bioetl.infrastructure.adapters.crossref.fetch_flow import CrossRefFetchFlow
from bioetl.infrastructure.adapters.crossref.query_builder import CrossRefQueryBuilder
from bioetl.infrastructure.adapters.crossref.response_mapper import (
    CrossRefResponseMapper,
)
from bioetl.infrastructure.adapters.crossref.types import (
    CrossRefBatchFetcher,
    CrossRefSearchPaginator,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

__all__ = [
    "CrossRefRuntimeServices",
    "build_crossref_fetch_flow",
    "build_crossref_runtime_services",
]


@dataclass(frozen=True, slots=True)
class CrossRefRuntimeServices:
    """Resolved CrossRef runtime collaborators after composition wiring."""

    query_builder: CrossRefQueryBuilder
    response_mapper: CrossRefResponseMapper
    batch_fetcher: CrossRefBatchFetcher
    search_paginator: CrossRefSearchPaginator
    fallback_handler: CrossRefTitleFallbackHandler


def _require_runtime_service[RuntimeService](
    value: RuntimeService | None,
    *,
    name: str,
) -> RuntimeService:
    """Fail fast when a mandatory runtime collaborator was not injected."""
    if value is None:
        raise ValueError(f"CrossRef adapter requires injected {name}")
    return value


def build_crossref_runtime_services(
    *,
    query_builder: CrossRefQueryBuilder | None,
    response_mapper: CrossRefResponseMapper | None,
    batch_fetcher: CrossRefBatchFetcher | None,
    search_paginator: CrossRefSearchPaginator | None,
    title_fallback_handler: CrossRefTitleFallbackHandler | None,
) -> CrossRefRuntimeServices:
    """Validate that composition injected the full CrossRef runtime graph."""
    return CrossRefRuntimeServices(
        query_builder=_require_runtime_service(
            query_builder,
            name="query_builder",
        ),
        response_mapper=_require_runtime_service(
            response_mapper,
            name="response_mapper",
        ),
        batch_fetcher=_require_runtime_service(
            batch_fetcher,
            name="batch_fetcher",
        ),
        search_paginator=_require_runtime_service(
            search_paginator,
            name="search_paginator",
        ),
        fallback_handler=_require_runtime_service(
            title_fallback_handler,
            name="title_fallback_handler",
        ),
    )


def build_crossref_fetch_flow(
    *,
    fetch_flow: CrossRefFetchFlow | None,
    logger: LoggerPort,
    batch_fetcher: CrossRefBatchFetcher,
    search_paginator: CrossRefSearchPaginator,
    fallback_decorator: ComposableFallbackDecorator,
    batch_size: int,
    response_mapper: CrossRefResponseMapper,
) -> CrossRefFetchFlow:
    """Resolve CrossRef fetch flow using injected override or default builder."""
    if fetch_flow is not None:
        return fetch_flow
    return _create_default_crossref_fetch_flow(
        logger=logger,
        batch_fetcher=batch_fetcher,
        search_paginator=search_paginator,
        fallback_decorator=fallback_decorator,
        batch_size=batch_size,
        response_mapper=response_mapper,
    )
