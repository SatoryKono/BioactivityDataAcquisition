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
"""Unit tests for CachedBronzeDataSource adapter."""

from __future__ import annotations

import asyncio
from tests.helpers.synthetic_paths import synthetic_test_root
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.async_utils import collect_async_iterator

from bioetl.domain.exceptions import StorageError
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters._cached_bronze_support import parse_bronze_date
from bioetl.infrastructure.adapters.cached_bronze_data_source import (
    CachedBronzeDataSource,
)

pytestmark = pytest.mark.unit

TEST_ROOT = synthetic_test_root("bioetl-cached-bronze-data-source")
BRONZE_ROOT = TEST_ROOT / "bronze"
BRONZE_ACTIVITY_ROOT = BRONZE_ROOT / "chembl" / "activity"


class _FakeBronzeReader:
    """Minimal async Bronze reader test double."""

    def __init__(
        self,
        *,
        base_path: str,
        flat_structure: bool,
        batches: list[str],
        records_by_batch: dict[str, list[dict[str, object]]],
    ) -> None:
        self.base_path = Path(base_path)
        self._flat_structure = flat_structure
        self._batches = batches
        self._records_by_batch = records_by_batch
        self.list_batches_calls: list[tuple[str, str, datetime | None]] = []

    async def list_batches(
        self, provider: str, entity: str, date: datetime | None = None
    ) -> list[str]:
        await asyncio.sleep(0)
        self.list_batches_calls.append((provider, entity, date))
        return list(self._batches)

    async def read_bronze(self, path: str):
        for record in self._records_by_batch.get(path, []):
            yield record


@pytest.fixture
def bound_logger() -> MagicMock:
    """Bound logger used by the adapter after logger.bind()."""
    logger = MagicMock()
    logger.warning = MagicMock()
    logger.info = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def base_logger(bound_logger: MagicMock) -> MagicMock:
    """Base logger that returns bound logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=bound_logger)
    return logger


@pytest.mark.unit
class TestCachedBronzeDataSourceBasics:
    """Basic behavior and protocol-like methods."""

    @pytest.mark.asyncio
    async def test_provider_name_health_and_context_manager(
        self, base_logger: MagicMock
    ) -> None:
        """Adapter should expose provider_name and no-op async lifecycle methods."""
        reader = _FakeBronzeReader(
            base_path=str(BRONZE_ROOT),
            flat_structure=False,
            batches=[],
            records_by_batch={},
        )
        source = CachedBronzeDataSource(
            bronze_reader=reader,
            provider="chembl",
            entity_type="activity",
            logger=base_logger,
        )

        assert source.provider_name == "chembl"
        assert await source.health_check() == HealthStatus.HEALTHY
        assert await source.__aenter__() is source
        await source.__aexit__(None, None, None)
        await source.aclose()

    def test_parse_bronze_date_returns_utc_datetime_and_supports_none(
        self,
        base_logger: MagicMock,
    ) -> None:
        """Canonical helper should return UTC-aware datetime and support None."""
        reader = _FakeBronzeReader(
            base_path=str(BRONZE_ROOT),
            flat_structure=False,
            batches=[],
            records_by_batch={},
        )
        _ = CachedBronzeDataSource(
            bronze_reader=reader,
            provider="chembl",
            entity_type="activity",
            logger=base_logger,
        )

        assert parse_bronze_date(None) is None
        parsed = parse_bronze_date("2026-03-01")
        assert parsed is not None
        assert parsed.tzinfo == UTC
        assert parsed.year == 2026
        assert parsed.month == 3
        assert parsed.day == 1


@pytest.mark.unit
class TestCachedBronzeDataSourceBatches:
    """Batch listing and deterministic ordering."""

    @pytest.mark.asyncio
    async def test_list_batches_sorted_standard_structure(
        self, base_logger: MagicMock
    ) -> None:
        """Standard structure should call list_batches(provider, entity, date)."""
        reader = _FakeBronzeReader(
            base_path=str(BRONZE_ROOT),
            flat_structure=False,
            batches=[
                "2026-01-02/batch_b.jsonl.zst",
                "2026-01-01/batch_a.jsonl.zst",
            ],
            records_by_batch={},
        )
        source = CachedBronzeDataSource(
            bronze_reader=reader,
            provider="chembl",
            entity_type="activity",
            logger=base_logger,
            bronze_date="2026-01-02",
        )

        batches = await source._list_batches_sorted()

        assert batches == [
            "2026-01-01/batch_a.jsonl.zst",
            "2026-01-02/batch_b.jsonl.zst",
        ]
        assert len(reader.list_batches_calls) == 1
        provider, entity, date = reader.list_batches_calls[0]
        assert provider == "chembl"
        assert entity == "activity"
        assert date is not None
        assert date.tzinfo == UTC

    @pytest.mark.asyncio
    async def test_list_batches_sorted_flat_structure(
        self, base_logger: MagicMock
    ) -> None:
        """Flat structure should pass empty provider/entity to list_batches()."""
        reader = _FakeBronzeReader(
            base_path=str(BRONZE_ACTIVITY_ROOT),
            flat_structure=True,
            batches=["2026-01-01/batch_a.jsonl.zst"],
            records_by_batch={},
        )
        source = CachedBronzeDataSource(
            bronze_reader=reader,
            provider="chembl",
            entity_type="activity",
            logger=base_logger,
        )

        batches = await source._list_batches_sorted()

        assert batches == ["2026-01-01/batch_a.jsonl.zst"]
        assert reader.list_batches_calls == [("", "", None)]


@pytest.mark.unit
class TestCachedBronzeDataSourceFetch:
    """Fetch semantics, empty cache error, and record counting."""

    @pytest.mark.asyncio
    async def test_fetch_raises_cached_bronze_empty(
        self, base_logger: MagicMock
    ) -> None:
        """When no batches exist, adapter should raise CachedBronzeEmptyError."""
        reader = _FakeBronzeReader(
            base_path="/data/bronze",
            flat_structure=False,
            batches=[],
            records_by_batch={},
        )
        source = CachedBronzeDataSource(
            bronze_reader=reader,
            provider="chembl",
            entity_type="activity",
            logger=base_logger,
        )

        with pytest.raises(StorageError) as exc_info:
            _ = await collect_async_iterator(source.fetch("activity"))

        error = exc_info.value
        assert error.provider == "chembl"
        assert error.entity_type == "activity"
        assert error.bronze_path.replace("\\", "/").endswith("chembl/activity")

    @pytest.mark.asyncio
    async def test_fetch_sorts_batches_warns_for_unsupported_params_and_applies_limit(
        self, base_logger: MagicMock, bound_logger: MagicMock
    ) -> None:
        """Fetch should be deterministic, log unsupported params, and respect limit."""
        reader = _FakeBronzeReader(
            base_path=str(BRONZE_ROOT),
            flat_structure=False,
            batches=[
                "2026-01-02/batch_b.jsonl.zst",
                "2026-01-01/batch_a.jsonl.zst",
            ],
            records_by_batch={
                "2026-01-01/batch_a.jsonl.zst": [{"id": 1}, {"id": 2}],
                "2026-01-02/batch_b.jsonl.zst": [{"id": 3}],
            },
        )
        source = CachedBronzeDataSource(
            bronze_reader=reader,
            provider="chembl",
            entity_type="activity",
            logger=base_logger,
        )

        records = await collect_async_iterator(
            source.fetch(
                "activity",
                limit=2,
                query="ignored-query",
                filter_ids=["1", "2"],
                filter_field="id",
                offset=10,
            )
        )

        assert records == [{"id": 1}, {"id": 2}]
        warning_events = [call.args[0] for call in bound_logger.warning.call_args_list]
        assert "cached_bronze_query_ignored" in warning_events
        assert "cached_bronze_filter_ignored" in warning_events

    @pytest.mark.asyncio
    async def test_fetch_completes_without_limit(
        self, base_logger: MagicMock, bound_logger: MagicMock
    ) -> None:
        """Fetch should complete and log when no limit is provided."""
        reader = _FakeBronzeReader(
            base_path=str(BRONZE_ROOT),
            flat_structure=False,
            batches=["2026-01-01/batch_a.jsonl.zst"],
            records_by_batch={"2026-01-01/batch_a.jsonl.zst": [{"id": 1}, {"id": 2}]},
        )
        source = CachedBronzeDataSource(
            bronze_reader=reader,
            provider="chembl",
            entity_type="activity",
            logger=base_logger,
        )

        records = await collect_async_iterator(source.fetch("activity"))

        assert records == [{"id": 1}, {"id": 2}]
        info_events = [call.args[0] for call in bound_logger.info.call_args_list]
        assert "cached_bronze_fetch_complete" in info_events

    @pytest.mark.asyncio
    async def test_get_total_records_counts_across_all_batches(
        self, base_logger: MagicMock
    ) -> None:
        """Total records should sum records from all listed batches."""
        reader = _FakeBronzeReader(
            base_path=str(BRONZE_ROOT),
            flat_structure=False,
            batches=["a.jsonl.zst", "b.jsonl.zst"],
            records_by_batch={
                "a.jsonl.zst": [{"id": 1}, {"id": 2}],
                "b.jsonl.zst": [{"id": 3}],
            },
        )
        source = CachedBronzeDataSource(
            bronze_reader=reader,
            provider="chembl",
            entity_type="activity",
            logger=base_logger,
        )

        total = await source.get_total_records()

        assert total == 3


def test_cached_bronze_health_check_does_not_emit_chembl_counters() -> None:
    source = object.__new__(CachedBronzeDataSource)
    assert "handle_health_check_result" not in source.health_check.__code__.co_names
    assert "bioetl_health_check_success_total" not in (
        source.health_check.__code__.co_consts or ()
    )
