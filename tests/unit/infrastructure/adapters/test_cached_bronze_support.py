"""Unit tests for private cached-Bronze support helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.domain.exceptions import StorageError
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters._cached_bronze_support import (
    BronzeBatchReader,
    log_unsupported_fetch_params,
    raise_if_empty_batches,
    resolve_bronze_path,
)


class _ReaderStub(BronzeBatchReader):
    """Minimal reader stub for cached-Bronze helper tests."""

    def __init__(self, *, base_path: Path, flat_structure: bool) -> None:
        self.base_path = base_path
        self._flat_structure = flat_structure

    async def list_batches(
        self,
        provider: str,
        entity: str,
        date: datetime | None = None,
    ) -> list[str]:
        raise AssertionError(
            f"list_batches should not be called in this test: {provider=} {entity=} {date=}"
        )

    def read_bronze(self, path: str) -> AsyncIterator[JsonDict]:
        class _FailingAsyncIterator:
            def __aiter__(self) -> _FailingAsyncIterator:
                return self

            async def __anext__(self) -> JsonDict:
                raise AssertionError(
                    f"read_bronze should not be called in this test: {path=}"
                )

        return _FailingAsyncIterator()


@pytest.mark.unit
def test_resolve_bronze_path_uses_base_path_for_flat_structure() -> None:
    """Flat layout should keep empty-cache errors anchored at base_path."""
    reader: BronzeBatchReader = _ReaderStub(
        base_path=Path("/tmp/bronze/chembl/activity"),
        flat_structure=True,
    )

    bronze_path = resolve_bronze_path(
        reader,
        provider="chembl",
        entity_type="activity",
    )

    assert bronze_path.replace("\\", "/").endswith("/tmp/bronze/chembl/activity")


@pytest.mark.unit
def test_resolve_bronze_path_appends_provider_and_entity_for_nested_layout() -> None:
    """Nested layout should point empty-cache errors at provider/entity path."""
    reader: BronzeBatchReader = _ReaderStub(
        base_path=Path("/tmp/bronze"),
        flat_structure=False,
    )

    bronze_path = resolve_bronze_path(
        reader,
        provider="chembl",
        entity_type="activity",
    )

    assert bronze_path.replace("\\", "/").endswith("/tmp/bronze/chembl/activity")


@pytest.mark.unit
def test_raise_if_empty_batches_raises_cached_bronze_empty_error() -> None:
    """Empty batch lists should raise the canonical cached-Bronze error."""
    reader: BronzeBatchReader = _ReaderStub(
        base_path=Path("/tmp/bronze"),
        flat_structure=False,
    )

    with pytest.raises(StorageError) as exc_info:
        raise_if_empty_batches(
            [],
            reader=reader,
            provider="chembl",
            entity_type="activity",
            bronze_date="2026-03-23",
        )

    error = exc_info.value
    assert error.provider == "chembl"
    assert error.entity_type == "activity"
    assert error.date_filter == "2026-03-23"
    assert error.bronze_path.replace("\\", "/").endswith("/tmp/bronze/chembl/activity")


@pytest.mark.unit
def test_raise_if_empty_batches_is_noop_when_batches_exist() -> None:
    """Non-empty batch lists should not raise."""
    reader: BronzeBatchReader = _ReaderStub(
        base_path=Path("/tmp/bronze"),
        flat_structure=False,
    )

    raise_if_empty_batches(
        ["2026-03-23/batch_a.jsonl.zst"],
        reader=reader,
        provider="chembl",
        entity_type="activity",
        bronze_date=None,
    )


@pytest.mark.unit
def test_log_unsupported_fetch_params_emits_only_for_present_fields() -> None:
    """Unsupported cached-Bronze fetch params should log only when provided."""
    logger = MagicMock()

    log_unsupported_fetch_params(
        logger,
        query="kinase",
        filter_ids=["CHEMBL1", "CHEMBL2"],
    )

    warning_events = [call.args[0] for call in logger.warning.call_args_list]
    assert warning_events == [
        "cached_bronze_query_ignored",
        "cached_bronze_filter_ignored",
    ]
