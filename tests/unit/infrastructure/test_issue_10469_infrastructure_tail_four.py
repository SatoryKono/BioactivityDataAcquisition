"""Behavioral coverage for adapter and storage guard tails in #10469."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

import pyarrow as pa
import pytest

from bioetl.infrastructure.adapters.common.composable_fallback import (
    ComposableFallbackDecorator,
    FallbackDecoratorConfig,
)
from bioetl.infrastructure.adapters.crossref._batch_support import BaseMetrics
from bioetl.infrastructure.adapters.crossref._client_fallback_policy import (
    _CrossRefFallbackPolicyMixin,
)
from bioetl.infrastructure.adapters.crossref._client_port_surface import (
    _CrossRefPortSurfaceMixin,
)
from bioetl.infrastructure.adapters.http.health_tracker import ProviderHealthTracker
from bioetl.infrastructure.adapters.http.pagination import PaginatedFetcherMixin
from bioetl.infrastructure.adapters.pubmed._fetch import PubMedFetchMixin
from bioetl.infrastructure.adapters.semanticscholar.batch_request_mixin import (
    SemanticScholarBatchRequestMixin,
)
from bioetl.infrastructure.audit._file_audit_io import FileAuditIOMixin
from bioetl.infrastructure.export.csv_exporter_table_ops import deduplicate_table
from bioetl.infrastructure.locking.memory_lock import MemoryLock


pytestmark = pytest.mark.unit


def test_fallback_decorator_silently_accepts_any_field_without_constraint() -> None:
    logger = Mock()
    decorator = ComposableFallbackDecorator(
        service=cast(Any, object()),
        strategy=cast(Any, object()),
        config=FallbackDecoratorConfig(supported_filter_field=None),
        logger=logger,
    )

    decorator._log_unsupported_filter_field("doi")

    logger.warning.assert_not_called()


def test_crossref_metrics_protocol_default_is_explicitly_abstract() -> None:
    with pytest.raises(NotImplementedError):
        BaseMetrics.measure_request(cast(Any, object()), "/works")


def test_crossref_fallback_policy_propagates_decorator_to_existing_flow() -> None:
    host = object.__new__(_CrossRefFallbackPolicyMixin)
    host._fetch_flow = SimpleNamespace(fallback_decorator=None)
    host._fallback_decorator = object()

    host._on_fallback_decorator_updated()

    assert host._fetch_flow.fallback_decorator is host._fallback_decorator


def test_crossref_port_surface_requires_initialized_fetch_flow() -> None:
    host = object.__new__(_CrossRefPortSurfaceMixin)
    host._fetch_flow = None

    with pytest.raises(RuntimeError, match="fetch flow is not initialized"):
        host._require_fetch_flow()


def test_provider_health_tracker_delegates_typed_result() -> None:
    result = object()
    monitor = Mock()
    monitor.update_from_health_check_result.return_value = "healthy"
    logger = Mock()
    tracker = ProviderHealthTracker("demo", monitor, logger)

    assert tracker.update(cast(Any, result)) == "healthy"
    monitor.update_from_health_check_result.assert_called_once_with(result, logger)


@pytest.mark.asyncio
async def test_paginated_fetch_rejects_nonpositive_page_limit() -> None:
    fetcher = PaginatedFetcherMixin()

    with pytest.raises(ValueError, match="max_pages must be >= 1"):
        _ = [
            row
            async for row in fetcher.paginated_fetch(
                lambda _cursor, _fetched: cast(Any, None), max_pages=0
            )
        ]


def test_pubmed_fetch_params_include_configured_real_api_key() -> None:
    host = object.__new__(PubMedFetchMixin)
    host.email = "ops@example.test"
    host.api_key = "real-key"

    assert host._build_fetch_params(["1"])["api_key"] == "real-key"


@pytest.mark.asyncio
async def test_semantic_scholar_empty_doi_batch_avoids_request() -> None:
    host = object.__new__(SemanticScholarBatchRequestMixin)

    assert [record async for record in host._fetch_by_dois([])] == []


def test_audit_reader_honors_zero_limit_before_file_parse(tmp_path: Path) -> None:
    audit_file = tmp_path / "audit_2026-09-16.jsonl"
    audit_file.write_text("not-json\n", encoding="utf-8")
    host = object.__new__(FileAuditIOMixin)
    host.base_path = tmp_path

    assert host._read_entries_sync(None, None, None, None, None, 0) == []


def test_csv_deduplication_returns_single_row_table_unchanged() -> None:
    table = pa.table({"id": [1], "value": ["only"]})
    logger = Mock()

    assert deduplicate_table(table, ["id"], logger=logger) is table
    logger.warning.assert_not_called()


@pytest.mark.asyncio
async def test_memory_lock_nonblocking_contention_returns_none() -> None:
    lock = MemoryLock()
    owner_one = cast(Any, "owner-1")
    owner_two = cast(Any, "owner-2")
    first = await lock.acquire("shared", owner_one)

    try:
        assert first is not None
        assert await lock.acquire("shared", owner_two, wait=False) is None
    finally:
        await lock.release("shared", owner_one)
        await lock.aclose()
