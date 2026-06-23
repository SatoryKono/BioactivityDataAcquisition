"""CrossRef datasource factory facade."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.composition.factories.datasource._crossref_inputs import (
    require_dependencies,
    resolve_mailto,
)
from bioetl.composition.factories.datasource._crossref_support import (
    build_crossref_components,
)
from bioetl.infrastructure.adapters.crossref import CrossRefAdapter

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.common.dependency_context import (
        HttpAdapterDependencyContext,
    )
    from bioetl.infrastructure.adapters.crossref.fetch_flow import CrossRefFetchFlow
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = ["create_crossref_adapter"]


def create_crossref_adapter(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: Settings | None,
    **kwargs: object,
) -> CrossRefAdapter:
    """Create a configured CrossRef adapter."""
    http_client_resolved, logger_resolved = require_dependencies(http_client, logger)
    components = build_crossref_components(
        kwargs=kwargs,
        http_client=http_client_resolved,
        logger=logger_resolved,
        settings=settings,
    )
    batch_size = cast(int, kwargs.get("batch_size", 50))
    dependency_context = cast(
        "HttpAdapterDependencyContext | None",
        kwargs.get("dependency_context"),
    )
    fetch_flow = cast("CrossRefFetchFlow | None", kwargs.get("fetch_flow"))
    mailto = resolve_mailto(kwargs, settings)

    return CrossRefAdapter(
        http_client=http_client_resolved,
        logger=logger_resolved,
        mailto=mailto,
        batch_size=batch_size,
        metrics=components.metrics,
        dependency_context=dependency_context,
        error_handler=components.error_handler,
        adapter_metrics=components.adapter_metrics,
        request_collector=components.request_collector,
        fallback_fetch_service=components.fallback_fetch_service,
        query_builder=components.query_builder,
        response_mapper=components.response_mapper,
        batch_fetcher=components.batch_fetcher,
        search_paginator=components.search_paginator,
        title_fallback_handler=components.title_fallback_handler,
        fetch_flow=fetch_flow,
    )
