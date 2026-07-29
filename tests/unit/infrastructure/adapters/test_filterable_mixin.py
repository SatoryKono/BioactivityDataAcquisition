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
"""Unit tests for filterable mixins used by adapter stubs."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest

from bioetl.infrastructure.adapters.filterable_mixin import (
    DelegatingFallbackMixin,
    FetchFilteredProtocol,
    NotSupportedMultiFilterMixin,
    iter_filtered_records_with_default_field,
)


class _DummyUnsupportedAdapter(NotSupportedMultiFilterMixin):
    provider_name = "dummy-provider"


class _DummyDelegatingAdapter(DelegatingFallbackMixin):
    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        await asyncio.sleep(0)
        del entity_type, filter_field, limit
        for item in filter_ids:
            yield {"id": item}


class _DummyDefaultFieldAdapter:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        self.calls.append(
            {
                "entity_type": entity_type,
                "filter_ids": filter_ids,
                "filter_field": filter_field,
                "limit": limit,
            }
        )
        for item in filter_ids:
            yield {"id": item}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_multi_filter_stub_raises_with_provider_name() -> None:
    await asyncio.sleep(0)
    adapter = _DummyUnsupportedAdapter()

    with pytest.raises(NotImplementedError, match="dummy-provider"):
        async for _ in adapter.fetch_multi_filtered(
            entity_type="publication",
            filters={"doi": ["10.1000/test"]},
            limit=10,
        ):
            continue


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fallback_mixin_delegates_to_fetch_filtered() -> None:
    await asyncio.sleep(0)
    adapter = _DummyDelegatingAdapter()

    result: list[dict[str, str]] = []
    async for item in adapter.fetch_filtered_with_fallback(
        entity_type="publication",
        filter_ids=["A", "B"],
        filter_field="doi",
        fallback_mapping={"A": "Title A"},
        limit=5,
    ):
        result.append(item)

    assert result == [{"id": "A"}, {"id": "B"}]


@pytest.mark.unit
def test_has_fetch_filtered_protocol_stub_callable() -> None:
    assert (
        FetchFilteredProtocol.fetch_filtered(
            object(),
            entity_type="publication",
            filter_ids=["1"],
            filter_field="doi",
            limit=1,
        )
        is None
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_iter_filtered_records_with_default_field_resolves_missing_field() -> (
    None
):
    adapter = _DummyDefaultFieldAdapter()

    result = [
        record
        async for record in iter_filtered_records_with_default_field(
            adapter,
            entity_type="publication",
            filter_ids=["A", "B"],
            filter_field=None,
            default_filter_field="doi",
            limit=2,
        )
    ]

    assert result == [{"id": "A"}, {"id": "B"}]
    assert adapter.calls == [
        {
            "entity_type": "publication",
            "filter_ids": ["A", "B"],
            "filter_field": "doi",
            "limit": 2,
        }
    ]
