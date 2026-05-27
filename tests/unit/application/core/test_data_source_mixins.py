"""Unit tests for source-metadata delegation mixin."""

from __future__ import annotations

import asyncio
import pytest

from bioetl.application.core._data_source_mixins import (
    _WrappedDataSourceDelegationMixin,
    _SourceMetadataDelegationMixin,
    _yield_plain_wrapped_fetch_records,
    _yield_wrapped_fetch_records,
)
from bioetl.domain.ports.health_check import HealthCheckResult
from bioetl.domain.types import HealthStatus


class _WrappedAdapter:
    def __init__(self) -> None:
        self.calls: list[str | None] = []

    def get_source_metadata(self, api_version: str | None = None) -> dict[str, str]:
        self.calls.append(api_version)
        return {"api_version": api_version or "none"}


class _DelegatingWrapper(_SourceMetadataDelegationMixin):
    def __init__(self, data_source: object) -> None:
        self._data_source = data_source


class _WrappedDelegatingWrapper(_WrappedDataSourceDelegationMixin):
    def __init__(self, data_source: object) -> None:
        self._data_source = data_source


def test_get_source_metadata_delegates_to_wrapped_data_source() -> None:
    wrapped = _WrappedAdapter()
    wrapper = _DelegatingWrapper(wrapped)

    result = wrapper.get_source_metadata("v2")

    assert result == {"api_version": "v2"}
    assert wrapped.calls == ["v2"]


def test_get_source_metadata_returns_none_when_method_missing() -> None:
    wrapper = _DelegatingWrapper(data_source=object())

    result = wrapper.get_source_metadata("v2")

    assert result is None


def test_get_source_metadata_returns_none_when_attribute_not_callable() -> None:
    class _NonCallableMetadataSource:
        get_source_metadata = "not-callable"

    wrapper = _DelegatingWrapper(data_source=_NonCallableMetadataSource())

    result = wrapper.get_source_metadata("v2")

    assert result is None


class _FetchRecordingAdapter:
    def __init__(self) -> None:
        self.fetch_calls: list[dict[str, object]] = []

    async def fetch(self, **kwargs: object):
        await asyncio.sleep(0)
        self.fetch_calls.append(kwargs)
        yield {"id": "1"}
        yield {"id": "2"}


@pytest.mark.asyncio
async def test_yield_wrapped_fetch_records_forwards_explicit_optional_kwargs() -> None:
    await asyncio.sleep(0)
    adapter = _FetchRecordingAdapter()

    records = [
        record
        async for record in _yield_wrapped_fetch_records(
            adapter,
            entity_type="publication",
            limit=10,
            query="kinase",
            filter_ids=None,
            filter_field=None,
            offset=25,
        )
    ]

    assert records == [{"id": "1"}, {"id": "2"}]
    assert adapter.fetch_calls == [
        {
            "entity_type": "publication",
            "limit": 10,
            "query": "kinase",
            "filter_ids": None,
            "filter_field": None,
            "offset": 25,
        }
    ]


@pytest.mark.asyncio
async def test_yield_plain_wrapped_fetch_records_omits_filter_kwargs() -> None:
    await asyncio.sleep(0)
    adapter = _FetchRecordingAdapter()

    records = [
        record
        async for record in _yield_plain_wrapped_fetch_records(
            adapter,
            entity_type="publication",
            limit=5,
            query="gene",
            offset=7,
        )
    ]

    assert records == [{"id": "1"}, {"id": "2"}]
    assert adapter.fetch_calls == [
        {
            "entity_type": "publication",
            "limit": 5,
            "query": "gene",
            "offset": 7,
        }
    ]


@pytest.mark.asyncio
async def test_check_health_delegates_to_wrapped_enhanced_method() -> None:
    class _EnhancedWrappedAdapter:
        provider_name = "chembl"

        async def check_health(self) -> HealthCheckResult:
            await asyncio.sleep(0)
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                latency_ms=12.5,
                provider="chembl",
                endpoint="/status",
            )

        async def health_check(self) -> HealthStatus:
            await asyncio.sleep(0)
            return HealthStatus.HEALTHY

    wrapper = _WrappedDelegatingWrapper(_EnhancedWrappedAdapter())

    result = await wrapper.check_health()

    assert result.provider == "chembl"
    assert result.status == HealthStatus.HEALTHY
    assert result.latency_ms == 12.5
    assert result.endpoint == "/status"


@pytest.mark.asyncio
async def test_check_health_synthesizes_result_from_legacy_health_check() -> None:
    class _LegacyWrappedAdapter:
        provider_name = "pubchem"

        async def health_check(self) -> HealthStatus:
            await asyncio.sleep(0)
            return HealthStatus.DEGRADED

    wrapper = _WrappedDelegatingWrapper(_LegacyWrappedAdapter())

    result = await wrapper.check_health()

    assert result.provider == "pubchem"
    assert result.status == HealthStatus.DEGRADED
    assert result.latency_ms == 0.0
    assert result.endpoint == ""
