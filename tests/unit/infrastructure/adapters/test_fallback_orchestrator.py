"""Unit tests for OpenAlexFallbackOrchestrator.

Tests the fallback chain execution: DOI-first primary fetch → title fallback,
phase-1 summary logging, limit propagation, and empty/error paths.

Source: src/bioetl/infrastructure/adapters/openalex/fallback_orchestrator.py
"""

from __future__ import annotations

from collections.abc import AsyncIterator
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service_yielding(
    records: list[BronzeRecord],
) -> FallbackFetchOrchestratorService:
    """Return a FallbackFetchOrchestratorService that yields the given records."""

    async def _fake_execute(
        request: FallbackFetchRequest,
    ) -> AsyncIterator[BronzeRecord]:
        for record in records:
            yield record

    service = MagicMock(spec=FallbackFetchOrchestratorService)
    service.execute = _fake_execute
    return service


def _make_orchestrator(
    records: list[BronzeRecord] | None = None,
    normalize_id: Any = None,
    extract_record_id: Any = None,
) -> OpenAlexFallbackOrchestrator:
    """Build an OpenAlexFallbackOrchestrator with sensible defaults."""
    service = _make_service_yielding(records or [])
    fallback_handler = MagicMock()
    logger = MagicMock()

    return OpenAlexFallbackOrchestrator(
        fallback_fetch_service=service,
        fallback_handler=fallback_handler,
        normalize_id=normalize_id or (lambda doi: doi.strip().lower() if doi else None),
        extract_record_id=extract_record_id or (lambda rec: str(rec.get("id", ""))),
        logger=logger,
    )


async def _collect(
    orchestrator: OpenAlexFallbackOrchestrator, **kwargs: Any
) -> list[BronzeRecord]:
    """Collect all records produced by orchestrator.execute(...)."""
    result: list[BronzeRecord] = []
    async for record in orchestrator.execute(**kwargs):
        result.append(record)
    return result


# ---------------------------------------------------------------------------
# Basic execution path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_yields_records_from_service() -> None:
    """execute() should yield every record produced by the underlying service."""
    expected = [
        {"id": "W123", "_lookup_method": "doi"},
        {"id": "W456", "_lookup_method": "title_fallback"},
    ]
    orchestrator = _make_orchestrator(records=expected)

    async def primary_fetcher(
        ids: list[str], limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        return
        yield  # make it an async generator

    results = await _collect(
        orchestrator,
        filter_ids=["10.1/a", "10.2/b"],
        fallback_mapping={"10.2/b": "Missing Title"},
        primary_record_fetcher=primary_fetcher,
        limit=None,
    )

    assert results == expected


@pytest.mark.asyncio
async def test_execute_returns_empty_when_service_yields_nothing() -> None:
    """execute() produces no output when the service returns zero records."""
    orchestrator = _make_orchestrator(records=[])

    async def primary_fetcher(
        ids: list[str], limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        return
        yield

    results = await _collect(
        orchestrator,
        filter_ids=["10.1/a"],
        fallback_mapping={},
        primary_record_fetcher=primary_fetcher,
        limit=None,
    )

    assert results == []


@pytest.mark.asyncio
async def test_execute_propagates_limit_to_service() -> None:
    """The limit parameter must be forwarded to FallbackFetchOrchestratorService."""
    captured_requests: list[FallbackFetchRequest] = []

    async def capturing_execute(
        request: FallbackFetchRequest,
    ) -> AsyncIterator[BronzeRecord]:
        captured_requests.append(request)
        return
        yield

    service = MagicMock(spec=FallbackFetchOrchestratorService)
    service.execute = capturing_execute
    logger = MagicMock()
    orchestrator = OpenAlexFallbackOrchestrator(
        fallback_fetch_service=service,
        fallback_handler=MagicMock(),
        normalize_id=lambda doi: doi,
        extract_record_id=lambda rec: str(rec.get("id", "")),
        logger=logger,
    )

    async def primary_fetcher(
        ids: list[str], limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        return
        yield

    await _collect(
        orchestrator,
        filter_ids=["10.1/a", "10.2/b"],
        fallback_mapping={},
        primary_record_fetcher=primary_fetcher,
        limit=5,
    )

    assert len(captured_requests) == 1
    assert captured_requests[0].limit == 5


@pytest.mark.asyncio
async def test_execute_propagates_filter_ids_and_fallback_mapping() -> None:
    """filter_ids and fallback_mapping must reach the service unchanged."""
    captured_requests: list[FallbackFetchRequest] = []

    async def capturing_execute(
        request: FallbackFetchRequest,
    ) -> AsyncIterator[BronzeRecord]:
        captured_requests.append(request)
        return
        yield

    service = MagicMock(spec=FallbackFetchOrchestratorService)
    service.execute = capturing_execute
    orchestrator = OpenAlexFallbackOrchestrator(
        fallback_fetch_service=service,
        fallback_handler=MagicMock(),
        normalize_id=lambda doi: doi,
        extract_record_id=lambda rec: str(rec.get("id", "")),
        logger=MagicMock(),
    )

    filter_ids = ["10.1/a", "10.2/b"]
    fallback_mapping = {"10.2/b": "Missing Work Title"}

    async def primary_fetcher(
        ids: list[str], limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        return
        yield

    await _collect(
        orchestrator,
        filter_ids=filter_ids,
        fallback_mapping=fallback_mapping,
        primary_record_fetcher=primary_fetcher,
        limit=None,
    )

    assert captured_requests[0].filter_ids == filter_ids
    assert captured_requests[0].fallback_mapping == fallback_mapping


@pytest.mark.asyncio
async def test_execute_sets_doi_as_primary_lookup_method() -> None:
    """The FallbackFetchRequest must use 'doi' as the primary_lookup_method."""
    captured_requests: list[FallbackFetchRequest] = []

    async def capturing_execute(
        request: FallbackFetchRequest,
    ) -> AsyncIterator[BronzeRecord]:
        captured_requests.append(request)
        return
        yield

    service = MagicMock(spec=FallbackFetchOrchestratorService)
    service.execute = capturing_execute
    orchestrator = OpenAlexFallbackOrchestrator(
        fallback_fetch_service=service,
        fallback_handler=MagicMock(),
        normalize_id=lambda doi: doi,
        extract_record_id=lambda rec: str(rec.get("id", "")),
        logger=MagicMock(),
    )

    async def primary_fetcher(
        ids: list[str], limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        return
        yield

    await _collect(
        orchestrator,
        filter_ids=["10.1/a"],
        fallback_mapping={},
        primary_record_fetcher=primary_fetcher,
        limit=None,
    )

    assert captured_requests[0].primary_lookup_method == "doi"


# ---------------------------------------------------------------------------
# Phase-1 summary logger
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_attaches_phase1_summary_logger_to_request() -> None:
    """A phase1_summary_logger callback must be attached in the FallbackFetchRequest."""
    captured_requests: list[FallbackFetchRequest] = []

    async def capturing_execute(
        request: FallbackFetchRequest,
    ) -> AsyncIterator[BronzeRecord]:
        captured_requests.append(request)
        return
        yield

    service = MagicMock(spec=FallbackFetchOrchestratorService)
    service.execute = capturing_execute
    logger = MagicMock()
    orchestrator = OpenAlexFallbackOrchestrator(
        fallback_fetch_service=service,
        fallback_handler=MagicMock(),
        normalize_id=lambda doi: doi,
        extract_record_id=lambda rec: str(rec.get("id", "")),
        logger=logger,
    )

    async def primary_fetcher(
        ids: list[str], limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        return
        yield

    await _collect(
        orchestrator,
        filter_ids=["10.1/a"],
        fallback_mapping={},
        primary_record_fetcher=primary_fetcher,
        limit=None,
    )

    # The orchestrator must provide a summary logger
    assert captured_requests[0].phase1_summary_logger is not None


@pytest.mark.asyncio
async def test_execute_phase1_summary_logger_calls_info_log() -> None:
    """Invoking the phase1_summary_logger must log via self.logger.info."""
    captured_requests: list[FallbackFetchRequest] = []

    async def capturing_execute(
        request: FallbackFetchRequest,
    ) -> AsyncIterator[BronzeRecord]:
        captured_requests.append(request)
        return
        yield

    service = MagicMock(spec=FallbackFetchOrchestratorService)
    service.execute = capturing_execute
    logger = MagicMock()
    logger.info = MagicMock()
    orchestrator = OpenAlexFallbackOrchestrator(
        fallback_fetch_service=service,
        fallback_handler=MagicMock(),
        normalize_id=lambda doi: doi,
        extract_record_id=lambda rec: str(rec.get("id", "")),
        logger=logger,
    )

    async def primary_fetcher(
        ids: list[str], limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        return
        yield

    await _collect(
        orchestrator,
        filter_ids=["10.1/a", "10.2/b"],
        fallback_mapping={},
        primary_record_fetcher=primary_fetcher,
        limit=None,
    )

    # Manually invoke the captured summary logger to verify it calls logger.info
    logger_fn = captured_requests[0].phase1_summary_logger
    assert logger_fn is not None
    logger_fn(total=10, found=7)

    logger.info.assert_called_once()
    call_args = logger.info.call_args
    assert call_args[0][0] == "openalex_doi_lookup_summary"


# ---------------------------------------------------------------------------
# normalize_id and extract_record_id delegation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_uses_injected_normalize_id() -> None:
    """The normalize_id callable injected into the orchestrator must be delegated."""
    captured_normalize: list[Any] = []

    def _normalizing(doi: str) -> str | None:
        captured_normalize.append(doi)
        return doi.lower()

    captured_requests: list[FallbackFetchRequest] = []

    async def capturing_execute(
        request: FallbackFetchRequest,
    ) -> AsyncIterator[BronzeRecord]:
        captured_requests.append(request)
        return
        yield

    service = MagicMock(spec=FallbackFetchOrchestratorService)
    service.execute = capturing_execute
    orchestrator = OpenAlexFallbackOrchestrator(
        fallback_fetch_service=service,
        fallback_handler=MagicMock(),
        normalize_id=_normalizing,
        extract_record_id=lambda rec: str(rec.get("id", "")),
        logger=MagicMock(),
    )

    async def primary_fetcher(
        ids: list[str], limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        return
        yield

    await _collect(
        orchestrator,
        filter_ids=["10.1/A"],
        fallback_mapping={},
        primary_record_fetcher=primary_fetcher,
        limit=None,
    )

    # Verify the normalize_id passed to the request is our function
    result = captured_requests[0].normalize_id("10.1/A")
    assert result == "10.1/a"


@pytest.mark.asyncio
async def test_execute_uses_injected_extract_record_id() -> None:
    """The extract_record_id callable must be delegated to the FallbackFetchRequest."""
    captured_requests: list[FallbackFetchRequest] = []

    async def capturing_execute(
        request: FallbackFetchRequest,
    ) -> AsyncIterator[BronzeRecord]:
        captured_requests.append(request)
        return
        yield

    service = MagicMock(spec=FallbackFetchOrchestratorService)
    service.execute = capturing_execute
    orchestrator = OpenAlexFallbackOrchestrator(
        fallback_fetch_service=service,
        fallback_handler=MagicMock(),
        normalize_id=lambda doi: doi,
        extract_record_id=lambda rec: str(rec.get("openalex_id", "missing")),
        logger=MagicMock(),
    )

    async def primary_fetcher(
        ids: list[str], limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        return
        yield

    await _collect(
        orchestrator,
        filter_ids=["10.1/a"],
        fallback_mapping={},
        primary_record_fetcher=primary_fetcher,
        limit=None,
    )

    record: BronzeRecord = {"openalex_id": "W9999"}
    extracted = captured_requests[0].extract_record_id(record)
    assert extracted == "W9999"


# ---------------------------------------------------------------------------
# Multiple records and limit boundary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_yields_all_records_when_no_limit() -> None:
    """With limit=None all records from the service must be returned."""
    records = [{"id": f"W{i}"} for i in range(10)]
    orchestrator = _make_orchestrator(records=records)

    async def primary_fetcher(
        ids: list[str], limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        return
        yield

    results = await _collect(
        orchestrator,
        filter_ids=[f"10.{i}/x" for i in range(10)],
        fallback_mapping={},
        primary_record_fetcher=primary_fetcher,
        limit=None,
    )

    assert len(results) == 10


@pytest.mark.asyncio
async def test_execute_with_empty_filter_ids() -> None:
    """execute() with an empty filter_ids list must complete without error."""
    orchestrator = _make_orchestrator(records=[])

    async def primary_fetcher(
        ids: list[str], limit: int | None
    ) -> AsyncIterator[BronzeRecord]:
        return
        yield

    results = await _collect(
        orchestrator,
        filter_ids=[],
        fallback_mapping={},
        primary_record_fetcher=primary_fetcher,
        limit=None,
    )

    assert results == []
