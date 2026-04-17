# mypy: disable-error-code=untyped-decorator

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import pytest

from bioetl.domain.exceptions import ExternalServiceError, RetryExhaustedError
from bioetl.infrastructure.adapters.common.fetch_resilience_template import (
    fetch_batch_with_reduction,
    retry_with_split_batches,
)


class _FakeRecoveryHost:
    def __init__(
        self,
        *,
        deduplicated_records: list[dict[str, str]] | None = None,
        deduplicated_error: Exception | None = None,
    ) -> None:
        self._logger = MagicMock()
        self.provider_name = "chembl"
        self.retry_exhausted_errors: set[Exception] = set()
        self.reduced_calls: list[list[str]] = []
        self.single_fallback_calls: list[tuple[list[str], str]] = []
        self._deduplicated_records = deduplicated_records or []
        self._deduplicated_error = deduplicated_error

    def _is_retry_exhausted_error(self, error: Exception) -> bool:
        return error in self.retry_exhausted_errors

    async def _fetch_batch_with_reduction(
        self,
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        limit: int | None,
        seen_ids: set[str],
        pk_field: str,
        pk_fields: tuple[str, ...] | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        del entity_type, filter_field, limit, seen_ids, pk_field, pk_fields
        self.reduced_calls.append(id_batch)
        yield {"id": ",".join(id_batch)}

    async def _yield_single_id_fallback(
        self,
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        seen_ids: set[str],
        pk_field: str,
        error: Exception,
        pk_fields: tuple[str, ...] | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        del entity_type, filter_field, seen_ids, pk_field, pk_fields
        self.single_fallback_calls.append((id_batch, str(error)))
        yield {"id": f"fallback:{id_batch[0]}"}

    async def _yield_deduplicated_filtered_records(
        self,
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        limit: int | None,
        seen_ids: set[str],
        pk_field: str,
        pk_fields: tuple[str, ...] | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        del entity_type, id_batch, filter_field, limit, seen_ids, pk_field, pk_fields
        if self._deduplicated_error is not None:
            raise self._deduplicated_error
        for record in self._deduplicated_records:
            yield record


@pytest.mark.asyncio
async def test_fetch_batch_with_reduction_yields_records_without_recovery() -> None:
    host = _FakeRecoveryHost(
        deduplicated_records=[{"id": "A"}, {"id": "B"}],
    )

    records = [
        record
        async for record in fetch_batch_with_reduction(
            host,
            "target",
            ["A", "B"],
            "target_chembl_id",
            None,
            set(),
            "target_id",
        )
    ]

    assert records == [{"id": "A"}, {"id": "B"}]
    assert host.reduced_calls == []
    assert host.single_fallback_calls == []


@pytest.mark.asyncio
async def test_fetch_batch_with_reduction_uses_single_id_fallback_on_retry_exhausted() -> None:
    retry_error = RetryExhaustedError("chembl://target", attempts=3)
    host = _FakeRecoveryHost(deduplicated_error=retry_error)
    host.retry_exhausted_errors.add(retry_error)

    records = [
        record
        async for record in fetch_batch_with_reduction(
            host,
            "target",
            ["CHEMBL1"],
            "target_chembl_id",
            None,
            set(),
            "target_id",
        )
    ]

    assert records == [{"id": "fallback:CHEMBL1"}]
    assert host.reduced_calls == []
    assert host.single_fallback_calls == [
        (["CHEMBL1"], str(retry_error)),
    ]


@pytest.mark.asyncio
async def test_fetch_batch_with_reduction_reraises_non_retry_service_error() -> None:
    service_error = ExternalServiceError("temporary upstream issue")
    host = _FakeRecoveryHost(deduplicated_error=service_error)

    with pytest.raises(ExternalServiceError, match="temporary upstream issue"):
        await anext(
            fetch_batch_with_reduction(
                host,
                "target",
                ["CHEMBL1", "CHEMBL2"],
                "target_chembl_id",
                None,
                set(),
                "target_id",
            )
        )


@pytest.mark.asyncio
async def test_retry_with_split_batches_logs_and_fetches_reduced_batches() -> None:
    host = _FakeRecoveryHost()
    retry_error = RetryExhaustedError("chembl://target", attempts=3)

    records = [
        record
        async for record in retry_with_split_batches(
            host,
            "target",
            ["1", "2", "3", "4"],
            "target_chembl_id",
            None,
            set(),
            "target_id",
            retry_error,
        )
    ]

    assert records == [{"id": "1,2"}, {"id": "3,4"}]
    assert host.reduced_calls == [["1", "2"], ["3", "4"]]
    assert host.single_fallback_calls == []
    host._logger.warning.assert_called_once_with(
        "batch_reduction_retry",
        provider="chembl",
        entity_type="target",
        original_batch_size=4,
        first_half_size=2,
        second_half_size=2,
        filter_field="target_chembl_id",
        error=str(retry_error),
    )
