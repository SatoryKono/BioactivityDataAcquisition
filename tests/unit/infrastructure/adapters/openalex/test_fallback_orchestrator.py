"""Unit tests for OpenAlexFallbackOrchestrator."""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common.fallback_fetch_service import (
    FallbackFetchOrchestratorService,
    FallbackFetchRequest,
)
from bioetl.infrastructure.adapters.openalex.fallback_orchestrator import (
    OpenAlexFallbackOrchestrator,
)

pytestmark = pytest.mark.unit


def _make_orchestrator(
    *,
    service: FallbackFetchOrchestratorService | None = None,
    fallback_handler: Any = None,
    normalize_id: Any = None,
    extract_record_id: Any = None,
    logger: Any = None,
) -> OpenAlexFallbackOrchestrator:
    """Build an OpenAlexFallbackOrchestrator with injectable collaborators."""
    return OpenAlexFallbackOrchestrator(
        fallback_fetch_service=service
        or MagicMock(spec=FallbackFetchOrchestratorService),
        fallback_handler=fallback_handler or MagicMock(),
        normalize_id=normalize_id or (lambda doi: doi.strip().lower() if doi else None),
        extract_record_id=extract_record_id or (lambda rec: str(rec.get("id", ""))),
        logger=logger or MagicMock(),
    )


async def _collect(
    orchestrator: OpenAlexFallbackOrchestrator, **kwargs: Any
) -> list[BronzeRecord]:
    """Collect all records produced by orchestrator.execute(...)."""
    result: list[BronzeRecord] = []
    async for record in orchestrator.execute(**kwargs):
        result.append(record)
    return result


@pytest.mark.asyncio
async def test_execute_builds_openalex_request_and_forwards_primary_fetcher() -> None:
    """execute() should bridge OpenAlex hooks/config into the shared service."""
    captured_requests: list[FallbackFetchRequest] = []
    forwarded: dict[str, Any] = {}
    fallback_handler = MagicMock()

    async def capture_execute(
        request: FallbackFetchRequest,
    ) -> AsyncIterator[BronzeRecord]:
        captured_requests.append(request)
        async for record in request.primary_record_fetcher(["10.1/A"], 5):
            yield record

    service = MagicMock(spec=FallbackFetchOrchestratorService)
    service.execute = capture_execute
    orchestrator = _make_orchestrator(
        service=service,
        fallback_handler=fallback_handler,
        normalize_id=lambda doi: doi.lower() if doi else None,
        extract_record_id=lambda rec: str(rec.get("openalex_id", "missing")),
    )

    async def primary_fetcher(
        ids: list[str], limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        forwarded["ids"] = list(ids)
        forwarded["limit"] = limit
        yield {"openalex_id": "W123", "_lookup_method": "doi"}

    results = await _collect(
        orchestrator,
        filter_ids=["10.1/A", "10.2/B"],
        fallback_mapping={"10.2/b": "Missing Title"},
        primary_record_fetcher=primary_fetcher,
        limit=5,
    )

    request = captured_requests[0]
    assert forwarded == {"ids": ["10.1/A"], "limit": 5}
    assert results == [{"openalex_id": "W123", "_lookup_method": "doi"}]
    assert request.filter_ids == ["10.1/A", "10.2/B"]
    assert request.fallback_mapping == {"10.2/b": "Missing Title"}
    assert request.limit == 5
    assert request.primary_lookup_method == "doi"
    assert request.fallback_operation == "fetch_filtered_with_fallback"
    assert request.resolve_fallback_handler() is fallback_handler
    assert request.resolve_normalize_id()("10.1/A") == "10.1/a"
    assert request.resolve_extract_record_id()({"openalex_id": "W9999"}) == "W9999"


@pytest.mark.asyncio
async def test_execute_attaches_openalex_phase1_summary_logger() -> None:
    """Summary logger should emit the OpenAlex DOI-lookup event with metrics."""
    captured_requests: list[FallbackFetchRequest] = []
    logger = MagicMock()
    logger.info = MagicMock()

    async def capture_execute(
        request: FallbackFetchRequest,
    ) -> AsyncIterator[BronzeRecord]:
        captured_requests.append(request)
        if False:
            yield {}

    service = MagicMock(spec=FallbackFetchOrchestratorService)
    service.execute = capture_execute
    orchestrator = _make_orchestrator(service=service, logger=logger)

    async def primary_fetcher(
        ids: list[str], limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        if False:
            yield {}

    await _collect(
        orchestrator,
        filter_ids=["10.1/a", "10.2/b"],
        fallback_mapping={},
        primary_record_fetcher=primary_fetcher,
        limit=None,
    )

    summary_logger = captured_requests[0].phase1_summary_logger
    assert summary_logger is not None

    summary_logger(total=10, found=7)

    logger.info.assert_called_once_with(
        "openalex_doi_lookup_summary",
        total_dois=10,
        found_by_doi=7,
        missing_dois=3,
        hit_rate_pct=70.0,
    )


@pytest.mark.asyncio
async def test_execute_skips_service_for_unsupported_filter_field() -> None:
    """OpenAlex fallback policy should reject unsupported non-DOI filter fields."""
    service = MagicMock(spec=FallbackFetchOrchestratorService)
    service.execute = MagicMock()
    logger = MagicMock()
    logger.warning = MagicMock()
    orchestrator = _make_orchestrator(service=service, logger=logger)

    async def primary_fetcher(
        ids: list[str], limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        if False:
            yield {}

    results = await _collect(
        orchestrator,
        filter_ids=["W123"],
        fallback_mapping={},
        primary_record_fetcher=primary_fetcher,
        limit=None,
        filter_field="openalex_id",
    )

    assert results == []
    service.execute.assert_not_called()
    logger.warning.assert_called_once_with(
        "unsupported_filter_field_for_fallback",
        field="openalex_id",
        expected="doi",
        msg="OpenAlex fallback only supports 'doi' filtering, skipping",
    )


@pytest.mark.asyncio
async def test_configure_policy_can_disable_fallback_handler() -> None:
    """configure_policy() should rebuild the decorator with updated policy settings."""
    captured_requests: list[FallbackFetchRequest] = []

    async def capture_execute(
        request: FallbackFetchRequest,
    ) -> AsyncIterator[BronzeRecord]:
        captured_requests.append(request)
        if False:
            yield {}

    service = MagicMock(spec=FallbackFetchOrchestratorService)
    service.execute = capture_execute
    fallback_handler = MagicMock()
    orchestrator = _make_orchestrator(
        service=service, fallback_handler=fallback_handler
    )

    orchestrator.configure_policy(
        SimpleNamespace(
            enabled=False,
            supported_filter_field="doi",
            skip_on_unsupported_filter_field=True,
            primary_lookup_method="doi",
            fallback_operation="fetch_filtered_with_fallback",
        )
    )

    async def primary_fetcher(
        ids: list[str], limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        if False:
            yield {}

    await _collect(
        orchestrator,
        filter_ids=["10.1/a"],
        fallback_mapping={},
        primary_record_fetcher=primary_fetcher,
        limit=None,
    )

    request = captured_requests[0]
    assert orchestrator.fallback_enabled is False
    assert request.resolve_fallback_handler() is None
    assert orchestrator._decorator.config.supported_filter_field == "doi"
    assert orchestrator._decorator.config.primary_lookup_method == "doi"
