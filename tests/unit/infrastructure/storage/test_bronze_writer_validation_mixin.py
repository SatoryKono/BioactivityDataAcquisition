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
"""Unit tests for BronzeWriterValidationMixin."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import datetime, timedelta, timezone, UTC
from typing import cast
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.storage.bronze.validation_mixin import (
    BronzeWriterValidationMixin,
)


class _Host(BronzeWriterValidationMixin):
    """Minimal host that wires the mixin for isolated testing."""

    def __init__(self, *, flat_structure: bool = False) -> None:
        self._flat_structure = flat_structure
        self.logger = MagicMock()


@pytest.mark.unit
class TestBronzeWriterValidationMixin:
    """Tests for Bronze input validation and path helpers."""

    def test_resolve_bronze_path_nested(self) -> None:
        """Nested structure should include provider/entity in the path."""
        host = _Host(flat_structure=False)
        result = host._resolve_bronze_path(
            "chembl", "activity", "2025-01-15", "data.jsonl.zst"
        )
        assert result == "chembl/activity/2025-01-15/data.jsonl.zst"

    def test_resolve_bronze_path_flat(self) -> None:
        """Flat structure should omit provider/entity from the path."""
        host = _Host(flat_structure=True)
        result = host._resolve_bronze_path(
            "chembl", "activity", "2025-01-15", "data.jsonl.zst"
        )
        assert result == "2025-01-15/data.jsonl.zst"

    def test_validate_bronze_names_valid(self) -> None:
        """Valid alphanumeric names with underscores should pass."""
        host = _Host()
        host._validate_bronze_names("chembl", "activity")
        host._validate_bronze_names("pubmed_api", "publication_type")

    def test_validate_bronze_names_invalid_provider(self) -> None:
        """Invalid provider name should raise ValueError."""
        host = _Host()
        with pytest.raises(ValueError, match="Invalid provider name"):
            host._validate_bronze_names("chem-bl", "activity")

    def test_validate_bronze_names_empty(self) -> None:
        """Empty provider name should raise ValueError."""
        host = _Host()
        with pytest.raises(ValueError, match="Invalid provider name"):
            host._validate_bronze_names("", "activity")

    def test_validate_records_iterator_none(self) -> None:
        """None records should raise TypeError."""
        host = _Host()
        validate_records = cast(
            Callable[[Iterator[bytes] | None], None],
            host._validate_records_iterator,
        )
        with pytest.raises(TypeError, match="records cannot be None"):
            validate_records(None)

    def test_validate_records_iterator_valid(self) -> None:
        """A valid iterator should pass without error."""
        host = _Host()
        host._validate_records_iterator(iter([b'{"id": 1}']))

    def test_validate_utc_datetime_naive_raises(self) -> None:
        """Naive datetime should raise ValueError."""
        host = _Host()
        naive_dt = datetime(2025, 1, 15, 12, 0, 0)
        with pytest.raises(ValueError, match="must be timezone-aware"):
            host._validate_utc_datetime(naive_dt, "ingestion_ts")

    def test_validate_utc_datetime_non_utc_raises(self) -> None:
        """Non-UTC datetime should raise ValueError."""
        host = _Host()
        non_utc = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone(timedelta(hours=3)))
        with pytest.raises(ValueError, match="must be UTC"):
            host._validate_utc_datetime(non_utc, "ingestion_ts")

    def test_validate_utc_datetime_valid(self) -> None:
        """UTC datetime should pass without error."""
        host = _Host()
        utc_dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        host._validate_utc_datetime(utc_dt, "ingestion_ts")

    def test_validate_json_records_valid(self) -> None:
        """Valid JSON bytes should pass through."""
        host = _Host()
        records = [b'{"id": 1}', b'{"id": 2}']
        validated = list(host._validate_json_records(iter(records)))
        assert validated == records

    def test_validate_json_records_invalid_raises(self) -> None:
        """Invalid JSON should raise BronzeValidationError."""
        from bioetl.domain.exceptions import StorageError

        host = _Host()
        records = [b'{"id": 1}', b"not-json"]
        with pytest.raises(StorageError):
            list(host._validate_json_records(iter(records)))
