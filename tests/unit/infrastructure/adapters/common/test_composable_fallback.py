from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.common.composable_fallback import (
    ComposableFallbackDecorator,
    FallbackDecoratorConfig,
    resolve_fallback_policy,
)
from bioetl.infrastructure.adapters.common.fallback_fetch_service import (
    DefaultFallbackExecution,
    FallbackFetchOrchestratorService,
    FallbackFetchRequest,
)


def _normalize_default(value: str) -> str:
    return value.strip().lower()


def _extract_record_id_default(record: dict[str, object]) -> str:
    return str(record.get("id", ""))


def _make_strategy(
    *,
    normalize_id: Any = None,
    extract_record_id: Any = None,
    fallback_handler: Any = None,
) -> DefaultFallbackExecution:
    return DefaultFallbackExecution(
        normalize_id_hook=normalize_id or _normalize_default,
        extract_record_id_hook=extract_record_id or _extract_record_id_default,
        fallback_handler_hook=fallback_handler or MagicMock(name="fallback_handler"),
    )


def _make_decorator(
    *,
    service: FallbackFetchOrchestratorService | None = None,
    strategy: DefaultFallbackExecution | None = None,
    config: FallbackDecoratorConfig | None = None,
    logger: Any = None,
) -> ComposableFallbackDecorator:
    return ComposableFallbackDecorator(
        service=service or MagicMock(spec=FallbackFetchOrchestratorService),
        strategy=strategy or _make_strategy(),
        config=config or FallbackDecoratorConfig(),
        logger=logger or MagicMock(),
    )


async def _collect(
    decorator: ComposableFallbackDecorator, **kwargs: Any
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    async for row in decorator.execute(**kwargs):
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_execute_builds_request_from_strategy_defaults() -> None:
    captured_requests: list[FallbackFetchRequest] = []
    strategy = _make_strategy()

    async def capture_execute(
        request: FallbackFetchRequest,
    ) -> AsyncIterator[dict[str, object]]:
        captured_requests.append(request)
        yield {"id": "from-service"}

    service = MagicMock(spec=FallbackFetchOrchestratorService)
    service.execute = capture_execute
    decorator = _make_decorator(
        service=service,
        strategy=strategy,
        config=FallbackDecoratorConfig(
            supported_filter_field="doi",
            primary_lookup_method="doi",
            trim_primary_ids_to_limit=True,
            fallback_operation="fallback_flow",
        ),
    )

    async def primary_fetcher(
        primary_ids: list[str], limit: int | None
    ) -> AsyncIterator[dict[str, object]]:
        del primary_ids, limit
        for _ in ():
            yield {}

    results = await _collect(
        decorator,
        filter_ids=["10.1/A", "__title_only_0__"],
        fallback_mapping={"10.1/a": "Title A"},
        primary_record_fetcher=primary_fetcher,
        limit=3,
        filter_field="doi",
    )

    request = captured_requests[0]
    assert results == [{"id": "from-service"}]
    assert request.filter_ids == ["10.1/A", "__title_only_0__"]
    assert request.fallback_mapping == {"10.1/a": "Title A"}
    assert request.limit == 3
    assert request.primary_lookup_method == "doi"
    assert request.trim_primary_ids_to_limit
    assert request.fallback_operation == "fallback_flow"
    assert request.resolve_normalize_id()(" 10.1/A ") == "10.1/a"
    assert request.resolve_extract_record_id()({"id": "rec-1"}) == "rec-1"
    assert request.resolve_fallback_handler() is strategy.fallback_handler


@pytest.mark.asyncio
async def test_execute_prefers_explicit_overrides_over_strategy_hooks() -> None:
    captured_requests: list[FallbackFetchRequest] = []
    strategy = _make_strategy(
        normalize_id=lambda value: "strategy-normalize",
        extract_record_id=lambda record: "strategy-extract",
        fallback_handler=MagicMock(name="strategy_handler"),
    )
    override_handler = MagicMock(name="override_handler")

    async def capture_execute(
        request: FallbackFetchRequest,
    ) -> AsyncIterator[dict[str, object]]:
        captured_requests.append(request)
        for _ in ():
            yield {}

    service = MagicMock(spec=FallbackFetchOrchestratorService)
    service.execute = capture_execute
    decorator = _make_decorator(service=service, strategy=strategy)

    async def primary_fetcher(
        primary_ids: list[str], limit: int | None
    ) -> AsyncIterator[dict[str, object]]:
        del primary_ids, limit
        for _ in ():
            yield {}

    await _collect(
        decorator,
        filter_ids=["10.1/A"],
        fallback_mapping={},
        primary_record_fetcher=primary_fetcher,
        limit=None,
        normalize_id=lambda value: "override-normalize",
        extract_record_id=lambda record: "override-extract",
        fallback_handler=override_handler,
    )

    request = captured_requests[0]
    assert request.resolve_normalize_id()("10.1/A") == "override-normalize"
    assert request.resolve_extract_record_id()({"id": "rec-1"}) == "override-extract"
    assert request.resolve_fallback_handler() is override_handler


@pytest.mark.asyncio
async def test_execute_skips_service_for_unsupported_filter_field_when_configured() -> (
    None
):
    logger = MagicMock()
    service = MagicMock(spec=FallbackFetchOrchestratorService)
    service.execute = MagicMock()
    decorator = _make_decorator(
        service=service,
        config=FallbackDecoratorConfig(
            supported_filter_field="doi",
            unsupported_filter_event="unsupported_filter_field_for_fallback",
            unsupported_filter_message="Only '{expected}' is supported",
            skip_on_unsupported_filter_field=True,
        ),
        logger=logger,
    )

    async def primary_fetcher(
        primary_ids: list[str], limit: int | None
    ) -> AsyncIterator[dict[str, object]]:
        del primary_ids, limit
        for _ in ():
            yield {}

    results = await _collect(
        decorator,
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
        msg="Only 'doi' is supported",
    )


@pytest.mark.asyncio
async def test_execute_logs_but_continues_when_unsupported_filter_is_permissive() -> (
    None
):
    logger = MagicMock()
    captured_requests: list[FallbackFetchRequest] = []

    async def capture_execute(
        request: FallbackFetchRequest,
    ) -> AsyncIterator[dict[str, object]]:
        captured_requests.append(request)
        yield {"id": "from-service"}

    service = MagicMock(spec=FallbackFetchOrchestratorService)
    service.execute = capture_execute
    decorator = _make_decorator(
        service=service,
        config=FallbackDecoratorConfig(
            supported_filter_field="pmid",
            unsupported_filter_event="unsupported_filter_field_for_fallback",
            unsupported_filter_message="Assuming '{expected}' semantics",
            skip_on_unsupported_filter_field=False,
        ),
        logger=logger,
    )

    async def primary_fetcher(
        primary_ids: list[str], limit: int | None
    ) -> AsyncIterator[dict[str, object]]:
        del primary_ids, limit
        for _ in ():
            yield {}

    results = await _collect(
        decorator,
        filter_ids=["10.1/a"],
        fallback_mapping={},
        primary_record_fetcher=primary_fetcher,
        limit=None,
        filter_field="doi",
    )

    assert results == [{"id": "from-service"}]
    assert len(captured_requests) == 1
    logger.warning.assert_called_once_with(
        "unsupported_filter_field_for_fallback",
        field="doi",
        expected="pmid",
        msg="Assuming 'pmid' semantics",
    )


def test_resolve_fallback_policy_returns_defaults_when_policy_missing() -> None:
    defaults = FallbackDecoratorConfig(
        supported_filter_field="doi",
        unsupported_filter_event="unsupported",
        unsupported_filter_message="Only '{expected}' allowed",
        skip_on_unsupported_filter_field=False,
        primary_lookup_method="doi",
        trim_primary_ids_to_limit=True,
        fallback_operation="fallback_flow",
    )

    enabled, resolved = resolve_fallback_policy(None, defaults=defaults)

    assert enabled
    assert resolved is defaults


def test_resolve_fallback_policy_sanitizes_partial_policy_values() -> None:
    defaults = FallbackDecoratorConfig(
        supported_filter_field="doi",
        unsupported_filter_event="unsupported",
        unsupported_filter_message="Only '{expected}' allowed",
        skip_on_unsupported_filter_field=True,
        primary_lookup_method="doi",
        trim_primary_ids_to_limit=False,
        fallback_operation="fallback_flow",
    )
    policy = SimpleNamespace(
        enabled=False,
        supported_filter_field="  pmid  ",
        unsupported_filter_event="  custom_event  ",
        unsupported_filter_message="  Use {expected}  ",
        skip_on_unsupported_filter_field=False,
        primary_lookup_method="  pmid  ",
        trim_primary_ids_to_limit=True,
        fallback_operation="  custom_operation  ",
    )

    enabled, resolved = resolve_fallback_policy(policy, defaults=defaults)

    assert not enabled
    assert resolved == FallbackDecoratorConfig(
        supported_filter_field="pmid",
        unsupported_filter_event="custom_event",
        unsupported_filter_message="Use {expected}",
        skip_on_unsupported_filter_field=False,
        primary_lookup_method="pmid",
        trim_primary_ids_to_limit=True,
        fallback_operation="custom_operation",
    )


def test_resolve_fallback_policy_falls_back_for_blank_or_invalid_values() -> None:
    defaults = FallbackDecoratorConfig(
        supported_filter_field="doi",
        unsupported_filter_event="unsupported",
        unsupported_filter_message="Only '{expected}' allowed",
        skip_on_unsupported_filter_field=True,
        primary_lookup_method="doi",
        trim_primary_ids_to_limit=False,
        fallback_operation="fallback_flow",
    )
    policy = SimpleNamespace(
        enabled="yes",
        supported_filter_field="   ",
        unsupported_filter_event="   ",
        unsupported_filter_message=None,
        skip_on_unsupported_filter_field="no",
        primary_lookup_method=123,
        trim_primary_ids_to_limit="yes",
        fallback_operation="   ",
    )

    enabled, resolved = resolve_fallback_policy(
        policy,
        defaults=defaults,
        default_enabled=False,
    )

    assert not enabled
    assert resolved == defaults
