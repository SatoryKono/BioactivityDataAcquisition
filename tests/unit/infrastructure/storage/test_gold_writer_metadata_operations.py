"""Unit tests for Gold writer metadata operations."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.storage.gold_writer_metadata_operations import (
    _GoldMergedMetadataWriteRequest,
    _GoldMetadataWriteRequest,
    _PreparedGoldMetadataWrite,
    _extract_delta_table_version,
    _maybe_prepare_gold_merged_metadata_write,
    _normalize_delta_version_value,
    _persist_gold_metadata_write,
    _prepare_gold_metadata_write,
)


@pytest.mark.unit
class TestNormalizeDeltaVersionValue:
    """Tests for Delta version normalization."""

    def test_int_value_passthrough(self) -> None:
        """Integer values should be returned as-is."""
        assert _normalize_delta_version_value(42) == 42

    def test_string_digit_converts_to_int(self) -> None:
        """String digits should be converted to int."""
        assert _normalize_delta_version_value("7") == 7
        assert _normalize_delta_version_value("  12  ") == 12

    def test_non_digit_string_returns_none(self) -> None:
        """Non-digit strings should return None."""
        assert _normalize_delta_version_value("abc") is None

    def test_none_input_returns_none(self) -> None:
        """None input should return None."""
        assert _normalize_delta_version_value(None) is None


@pytest.mark.unit
class TestExtractDeltaTableVersion:
    """Tests for DeltaTable version extraction."""

    def test_extracts_version_from_callable(self) -> None:
        """Should call .version() and return normalized value."""
        table = MagicMock()
        table.version.return_value = 5
        assert _extract_delta_table_version(table) == 5

    def test_returns_none_when_no_version_attr(self) -> None:
        """Should return None when object has no version attribute."""
        table = object()
        assert _extract_delta_table_version(table) is None

    def test_returns_none_when_version_not_callable(self) -> None:
        """Should return None when version is not callable."""
        table = MagicMock()
        table.version = "not_callable_string"
        # version is now a string, but MagicMock makes it callable
        # Use a plain object instead
        table2 = MagicMock(spec=[])
        table2.version = 42  # int, not callable
        assert _extract_delta_table_version(table2) is None


@pytest.mark.unit
class TestPrepareGoldMetadataWrite:
    """Tests for standard Gold metadata preparation."""

    def test_resolves_provider_entity_and_builds_metadata(self) -> None:
        """Should call host methods to resolve provider/entity and build metadata."""
        host = MagicMock()
        host._metadata_coordinator = None
        host._transform_version = "1.0.0"
        host._transform_steps = ("normalize",)

        from bioetl.domain.medallion import GoldWriteMode

        request = _GoldMetadataWriteRequest(
            table_path="/tmp/gold/chembl_compound",
            table_name="chembl_compound",
            records=[{"id": 1}],
            mode=GoldWriteMode.APPEND,
            scd_config=None,
            ingestion_ts=None,
            run_id=None,
        )
        metadata = MagicMock()
        from unittest.mock import patch

        with patch(
            "bioetl.infrastructure.storage.gold_writer_metadata_operations.build_gold_metadata_payload",
            return_value=metadata,
        ) as mock_build:
            prepared = _prepare_gold_metadata_write(host, request)

        assert isinstance(prepared, _PreparedGoldMetadataWrite)
        assert prepared.provider_name == "chembl"
        assert prepared.entity_name == "compound"
        assert prepared.metadata is metadata
        mock_build.assert_called_once()


@pytest.mark.unit
class TestPersistGoldMetadataWrite:
    """Tests for Gold metadata persistence."""

    @pytest.mark.asyncio
    async def test_calls_write_gold_metadata_file(self) -> None:
        """Should delegate to host._write_gold_metadata_file."""
        host = AsyncMock()
        metadata = MagicMock()

        from bioetl.domain.medallion import GoldWriteMode

        request = _GoldMetadataWriteRequest(
            table_path="/tmp/gold/chembl_compound",
            table_name="chembl_compound",
            records=[{"id": 1}],
            mode=GoldWriteMode.APPEND,
            scd_config=None,
            ingestion_ts=None,
            run_id=None,
        )
        prepared = _PreparedGoldMetadataWrite(
            request=request,
            provider_name="chembl",
            entity_name="compound",
            metadata=metadata,
        )
        await _persist_gold_metadata_write(host, prepared)
        host._write_gold_metadata_file.assert_awaited_once()


@pytest.mark.unit
class TestMaybePrepareGoldMergedMetadataWrite:
    """Tests for conditional merged metadata preparation."""

    def test_returns_none_when_records_empty(self) -> None:
        """Should skip when records list is empty."""
        host = MagicMock()
        request = _GoldMergedMetadataWriteRequest(
            table_path="/tmp/gold/merged",
            table_name="merged_table",
            records=[],
        )
        result = _maybe_prepare_gold_merged_metadata_write(host, request)
        assert result is None

    def test_returns_none_when_coordinator_is_none(self) -> None:
        """Should skip and log when metadata coordinator is not configured."""
        host = MagicMock()
        host._metadata_coordinator = None
        host._transform_version = "1.0.0"
        host._transform_steps = ()
        request = _GoldMergedMetadataWriteRequest(
            table_path="/tmp/gold/merged",
            table_name="merged_table",
            records=[{"id": 1}],
        )
        result = _maybe_prepare_gold_merged_metadata_write(host, request)
        assert result is None
        host.logger.debug.assert_called_once()

    def test_prepares_merged_metadata_via_module_helper(self) -> None:
        host = MagicMock()
        host._metadata_coordinator = MagicMock()
        host._metadata_coordinator.create_gold_metadata.return_value = MagicMock()
        host._transform_version = "2.0.0"
        host._transform_steps = ("normalize",)
        request = _GoldMergedMetadataWriteRequest(
            table_path="/tmp/gold/merged",
            table_name="composite.publication",
            records=[{"id": 1}],
        )

        prepared = _maybe_prepare_gold_merged_metadata_write(host, request)

        assert prepared is not None
        host._metadata_coordinator.create_gold_metadata.assert_called_once()
        input_arg = host._metadata_coordinator.create_gold_metadata.call_args.args[0]
        assert input_arg.transform_version == "2.0.0"
        assert prepared.provider_name == "composite"
        assert prepared.entity_name == "publication"
