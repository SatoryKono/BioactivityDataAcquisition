# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.adapters.common import FallbackFetchOrchestrator
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.openalex.client_runtime_helpers import (
    OpenAlexRuntimeServicesRequest,
    _coerce_openalex_runtime_services_request,
    build_openalex_runtime_services,
    build_openalex_runtime_services_from_request,
)


pytestmark = pytest.mark.unit


def _build_legacy_kwargs() -> dict[str, object]:
    return {
        "fallback_fetch_service": FallbackFetchOrchestrator(),
        "openalex_query_executor": None,
        "openalex_response_mapper": None,
        "openalex_cursor_flow": None,
        "title_fallback_handler": None,
        "openalex_fallback_orchestrator": None,
        "http_client": MagicMock(),
        "adapter_metrics": MagicMock(),
        "request_collector": APIRequestCollector(),
        "headers_provider": lambda: {"User-Agent": "BioETL/1.0"},
        "api_base": "https://api.openalex.org",
        "mailto": "bioetl@example.org",
        "api_key": "openalex-key",
        "batch_size": 25,
        "title_search_cache_size": 3,
        "normalize_doi": lambda value: value.strip().lower() or None,
        "escape_title_for_search": lambda value: value.replace(" ", "+"),
        "extract_record_id": lambda record: str(record.get("id")),
        "search_by_title": AsyncMock(return_value=[]),
        "logger": MagicMock(),
        "runtime_errors": (RuntimeError,),
    }


def test_coerce_openalex_runtime_services_request_rejects_kwargs_with_request() -> None:
    request = OpenAlexRuntimeServicesRequest(**_build_legacy_kwargs())

    with pytest.raises(
        TypeError, match="unexpected keyword arguments with request object"
    ):
        _coerce_openalex_runtime_services_request(request, unexpected=True)


def test_coerce_openalex_runtime_services_request_rejects_unexpected_legacy_kwargs() -> (
    None
):
    kwargs = _build_legacy_kwargs()
    kwargs["unexpected"] = True

    with pytest.raises(TypeError, match="unexpected keyword arguments: unexpected"):
        _coerce_openalex_runtime_services_request(None, **kwargs)


def test_coerce_openalex_runtime_services_request_builds_request_from_legacy_kwargs() -> (
    None
):
    kwargs = _build_legacy_kwargs()

    request = _coerce_openalex_runtime_services_request(None, **kwargs)

    assert isinstance(request, OpenAlexRuntimeServicesRequest)
    assert request.api_key == "openalex-key"
    assert request.api_base == "https://api.openalex.org"
    assert request.batch_size == 25
    assert request.title_search_cache_size == 3
    assert request.search_by_title is not None


def test_build_openalex_runtime_services_from_request_alias_matches_primary_builder() -> (
    None
):
    request = OpenAlexRuntimeServicesRequest(**_build_legacy_kwargs())

    via_primary = build_openalex_runtime_services(request)
    via_alias = build_openalex_runtime_services_from_request(request)

    assert type(via_alias.query_executor) is type(via_primary.query_executor)
    assert type(via_alias.response_mapper) is type(via_primary.response_mapper)
    assert type(via_alias.cursor_flow) is type(via_primary.cursor_flow)
    assert type(via_alias.fallback_handler) is type(via_primary.fallback_handler)
    assert type(via_alias.fallback_orchestrator) is type(
        via_primary.fallback_orchestrator
    )
    assert via_alias.fallback_fetch_service is request.fallback_fetch_service
    assert via_alias.cursor_flow.query_executor is via_alias.query_executor
    assert via_alias.cursor_flow.response_mapper is via_alias.response_mapper
    assert (
        via_alias.fallback_orchestrator.fallback_handler is via_alias.fallback_handler
    )
