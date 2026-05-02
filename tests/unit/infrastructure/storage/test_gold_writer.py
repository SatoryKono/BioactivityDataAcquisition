"""Unit tests for GoldWriter."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pyarrow as pa
import pytest
from deltalake.exceptions import TableNotFoundError
from pandera.pandas import Column, DataFrameSchema

from bioetl.domain.types import GoldSchemaPolicyByVersion, GoldSchemaVersionPolicy
from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
from bioetl.infrastructure.storage.gold.runtime_helpers import (
    GoldWriterRuntimeServices,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    normalize_scd_config,
    set_gold_write_span_attributes,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.storage.gold_writer import GoldWriter


TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioetl-gold-writer-"))
GOLD_ROOT = str(TEST_ROOT / "gold")


@cache
def _gold_writer_cls() -> type[GoldWriter]:
    from bioetl.infrastructure.storage.gold_writer import GoldWriter

    return GoldWriter


def _build_gold_writer(**kwargs: object) -> GoldWriter:
    return _gold_writer_cls()(**kwargs)


@pytest.fixture
def gold_writer(noop_logger):
    """Create a GoldWriter instance."""
    return _build_gold_writer(base_path="s3://test-bucket/gold", logger=noop_logger)


@pytest.fixture
def strict_schema():
    """Create a strict Pandera schema for testing."""
    return DataFrameSchema(
        {
            "entity_id": Column(str, nullable=False),
            "value": Column(float, nullable=False),
        },
        strict=True,
    )


@pytest.fixture
def non_strict_schema():
    """Create a non-strict Pandera schema for testing."""
    return DataFrameSchema(
        {
            "entity_id": Column(str, nullable=False),
        },
        strict=False,
    )


@pytest.fixture
def legacy_schema():
    """Create a legacy strict schema for versioned Gold dual-write tests."""
    return DataFrameSchema(
        {
            "entity_id": Column(str, nullable=False),
            "legacy_value": Column(str, nullable=False),
        },
        strict=True,
    )


@pytest.fixture
def valid_records():
    """Create valid records for testing."""
    return [
        {"entity_id": "CHEMBL123", "value": 5.5},
        {"entity_id": "CHEMBL456", "value": 7.2},
    ]


@pytest.fixture
def fixed_ingestion_ts():
    """Create a fixed timestamp for testing SCD2 operations."""
    return datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)


@pytest.mark.unit
class TestGoldWriterWriteModeEnum:
    """Tests for GoldWriteMode enum."""

    def test_gold_write_mode_values(self):
        """Test all valid GoldWriteMode values."""
        from bioetl.infrastructure.storage.gold_writer import GoldWriteMode

        assert GoldWriteMode.OVERWRITE.value == "overwrite"
        assert GoldWriteMode.APPEND.value == "append"
        assert GoldWriteMode.SCD2.value == "scd2"

    def test_gold_write_mode_from_string(self):
        """Test creating GoldWriteMode from string."""
        from bioetl.infrastructure.storage.gold_writer import GoldWriteMode

        assert GoldWriteMode("overwrite") == GoldWriteMode.OVERWRITE
        assert GoldWriteMode("append") == GoldWriteMode.APPEND
        assert GoldWriteMode("scd2") == GoldWriteMode.SCD2

    def test_gold_write_mode_invalid_raises(self):
        """Test invalid mode string raises ValueError."""
        from bioetl.infrastructure.storage.gold_writer import GoldWriteMode

        with pytest.raises(ValueError):
            GoldWriteMode("invalid")

        with pytest.raises(ValueError):
            GoldWriteMode("merge")  # Valid for Silver, not Gold

        with pytest.raises(ValueError):
            GoldWriteMode("OVERWRITE")  # Case sensitive


@pytest.mark.unit
class TestGoldWriterInit:
    """Tests for GoldWriter initialization."""

    def test_init_strips_trailing_slash(self, noop_logger):
        """Test that trailing slash is stripped from base_path."""
        writer = _build_gold_writer(base_path="s3://bucket/gold/", logger=noop_logger)
        assert writer.base_path == "s3://bucket/gold"

    def test_init_with_csv_exporter(self, noop_logger):
        """Test initialization with CSV exporter."""
        from unittest.mock import MagicMock

        mock_exporter = MagicMock()
        writer = _build_gold_writer(
            base_path=GOLD_ROOT,
            logger=noop_logger,
            csv_exporter=mock_exporter,
        )
        assert writer.csv_exporter is mock_exporter

    def test_init_without_csv_exporter(self, noop_logger):
        """Test initialization without CSV exporter."""
        writer = _build_gold_writer(base_path=GOLD_ROOT, logger=noop_logger)
        assert writer.csv_exporter is None


@pytest.mark.unit
class TestGoldWriterPipelineHelpers:
    """Tests for extracted Gold write pipeline helpers."""

    def test_normalize_scd_config_returns_same_instance(self):
        """Normalization helper should preserve typed ScdConfig instances."""
        scd_config = MagicMock()

        assert (
            normalize_scd_config(scd_config, primary_keys=["entity_id"]) is scd_config
        )

    def test_set_gold_write_span_attributes_sets_standard_fields(self):
        """Span helper should write the standard Gold observability attributes."""
        span = MagicMock()

        set_gold_write_span_attributes(span, "test.table", "append", 2)

        assert span.set_attribute.call_args_list == [
            (("table_name", "test.table"), {}),
            (("mode", "append"), {}),
            (("record_count", 2), {}),
        ]

    @pytest.mark.asyncio
    async def test_write_gold_uses_injected_tracer(
        self, noop_logger, valid_records, strict_schema
    ) -> None:
        """Gold writer should open a span when tracing is injected."""
        tracer = MagicMock()
        span = MagicMock()
        span_cm = MagicMock()
        span_cm.__enter__.return_value = span
        span_cm.__exit__.return_value = None
        tracer.start_as_current_span.return_value = span_cm
        tracing = MagicMock()
        tracing.get_tracer.return_value = tracer

        writer = _build_gold_writer(
            base_path=GOLD_ROOT,
            logger=noop_logger,
            tracing=tracing,
        )
        writer._prepare_write_gold = AsyncMock(  # type: ignore[method-assign]
            return_value=MagicMock()
        )
        writer._dispatch_write = AsyncMock()  # type: ignore[method-assign]
        writer._post_write_gold = AsyncMock()  # type: ignore[method-assign]

        await writer.write_gold(
            table_name="test.table",
            records=valid_records,
            schema=strict_schema,
            mode="append",
        )

        tracing.get_tracer.assert_called_once()
        tracer.start_as_current_span.assert_called_once_with("write_gold")
        span.set_attribute.assert_any_call("table_name", "test.table")
        span.set_attribute.assert_any_call("mode", "append")


@pytest.mark.unit
class TestGoldWriterValidation:
    """Tests for GoldWriter validation."""

    async def test_write_gold_empty_records_raises(self, gold_writer, strict_schema):
        """Test write_gold raises ValueError for empty records."""
        with pytest.raises(ValueError, match="No records to write"):
            await gold_writer.write_gold(
                table_name="test.table",
                records=[],
                schema=strict_schema,
                mode="overwrite",
            )

    async def test_write_gold_non_strict_schema_raises(
        self, gold_writer, non_strict_schema, valid_records
    ):
        """Test write_gold raises ValueError for non-strict schema."""
        with pytest.raises(ValueError, match="strict=True"):
            await gold_writer.write_gold(
                table_name="test.table",
                records=valid_records,
                schema=non_strict_schema,
                mode="overwrite",
            )

    async def test_write_gold_invalid_mode_raises(
        self, gold_writer, valid_records, strict_schema
    ):
        """Test write_gold raises ValueError for invalid mode."""
        with pytest.raises(ValueError, match="Invalid Gold write mode"):
            await gold_writer.write_gold(
                table_name="test.table",
                records=valid_records,
                schema=strict_schema,
                mode="invalid",
            )

    async def test_prepare_write_gold_returns_named_context(
        self, gold_writer, valid_records, strict_schema
    ):
        """Test _prepare_write_gold returns a named pre-write context."""
        prepared = await gold_writer._prepare_write_gold(
            table_name="test.table",
            records=valid_records,
            mode="overwrite",
            schema=strict_schema,
            scd_config=None,
            ingestion_ts=None,
        )

        assert prepared.table_name == "test.table"
        assert prepared.table_path == "s3://test-bucket/gold/test/table"
        assert prepared.validated_mode.value == "overwrite"

    async def test_write_gold_dispatches_named_context(
        self, gold_writer, valid_records, strict_schema
    ):
        """Test write_gold routes a named request/prepared context into dispatch."""
        from bioetl.infrastructure.storage.gold_writer import (
            GoldWriteMode,
            _PreparedGoldWriteContext,
        )

        prepared = _PreparedGoldWriteContext(
            table_name="test.table",
            table_path="s3://test-bucket/gold/test/table",
            validated_mode=GoldWriteMode.APPEND,
        )
        gold_writer._prepare_write_gold = AsyncMock(  # type: ignore[method-assign]
            return_value=prepared
        )
        gold_writer._dispatch_write = AsyncMock()  # type: ignore[method-assign]
        gold_writer._post_write_gold = AsyncMock()  # type: ignore[method-assign]

        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            schema=strict_schema,
            mode="append",
            primary_keys=["entity_id"],
            partition_cols=["year"],
        )

        gold_writer._prepare_write_gold.assert_awaited_once()
        gold_writer._dispatch_write.assert_awaited_once()
        dispatch_context = gold_writer._dispatch_write.await_args.args[0]
        assert dispatch_context.prepared is prepared
        assert dispatch_context.request.table_name == "test.table"
        assert dispatch_context.request.records == valid_records
        assert dispatch_context.request.schema is strict_schema
        assert dispatch_context.request.mode == "append"
        assert dispatch_context.request.primary_keys == ["entity_id"]
        assert dispatch_context.request.partition_cols == ["year"]

        post_context = gold_writer._post_write_gold.await_args.args[0]
        assert post_context.prepared is prepared
        assert post_context.records == valid_records
        assert post_context.schema is strict_schema

    async def test_write_gold_scd2_without_config_raises(
        self, gold_writer, valid_records, strict_schema
    ):
        """Test write_gold raises ValueError for SCD2 mode without config."""
        with pytest.raises(ValueError, match="scd_config required"):
            await gold_writer.write_gold(
                table_name="test.table",
                records=valid_records,
                schema=strict_schema,
                mode="scd2",
            )

    async def test_write_gold_scd2_without_ingestion_ts_raises(
        self, gold_writer, valid_records, strict_schema
    ):
        """Test write_gold raises ValueError for SCD2 mode without ingestion_ts."""
        scd_config = {"business_key": "entity_id"}
        with pytest.raises(ValueError, match="ingestion_ts required"):
            await gold_writer.write_gold(
                table_name="test.table",
                records=valid_records,
                schema=strict_schema,
                mode="scd2",
                scd_config=scd_config,
            )


@pytest.mark.unit
class TestGoldWriterDualWrite:
    """Tests for Gold dual-write rollout semantics."""

    async def test_write_gold_dual_write_dispatches_all_versioned_targets(
        self,
        noop_logger,
        strict_schema,
        legacy_schema,
    ):
        """Gold dual-write resolves versioned tables and schema per contract version."""
        rollout_policy = ContractRolloutPolicy(
            contract_ref="pubmed/publication",
            active_version="2.0.0",
            mode="dual_write",
            read_order=("2.0.0", "1.0.0"),
            write_versions=("1.0.0", "2.0.0"),
        )
        writer = _build_gold_writer(
            base_path="s3://test-bucket/gold",
            logger=noop_logger,
            runtime_services=GoldWriterRuntimeServices(
                csv_exporter=None,
                tracing=MagicMock(),
                metrics=None,
                audit=None,
                metadata_writer=MagicMock(),
                metadata_coordinator=None,
                lineage_store=None,
                contract_rollout_policy=rollout_policy,
            ),
        )
        writer._prepare_write_gold = AsyncMock(  # type: ignore[method-assign]
            side_effect=lambda **kwargs: MagicMock(
                table_name=kwargs["table_name"],
                table_path=f"s3://test-bucket/gold/{kwargs['table_name'].replace('.', '/')}",
                validated_mode=MagicMock(value=kwargs["mode"]),
            )
        )
        writer._dispatch_write = AsyncMock()  # type: ignore[method-assign]
        writer._post_write_gold = AsyncMock()  # type: ignore[method-assign]

        await writer.write_gold(
            table_name="test.table",
            records=[
                {
                    "entity_id": "CHEMBL123",
                    "legacy_value": "old",
                    "value": 5.5,
                    "extra": "drop_me",
                }
            ],
            schema=GoldSchemaPolicyByVersion(
                active_version="2.0.0",
                policies=(
                    GoldSchemaVersionPolicy(version="1.0.0", schema=legacy_schema),
                    GoldSchemaVersionPolicy(version="2.0.0", schema=strict_schema),
                ),
            ),
            mode="append",
        )

        prepare_calls = writer._prepare_write_gold.await_args_list
        assert [call.kwargs["table_name"] for call in prepare_calls] == [
            "test.table__v1_0_0",
            "test.table__v2_0_0",
        ]
        assert prepare_calls[0].kwargs["records"] == [
            {"entity_id": "CHEMBL123", "legacy_value": "old"}
        ]
        assert prepare_calls[1].kwargs["records"] == [
            {"entity_id": "CHEMBL123", "value": 5.5}
        ]
        assert writer._dispatch_write.await_count == 2
        assert writer._post_write_gold.await_count == 2

    async def test_write_gold_dual_write_fails_logical_write_when_any_target_fails(
        self,
        noop_logger,
        strict_schema,
        legacy_schema,
    ):
        """Any versioned Gold target failure should fail the whole logical write."""
        rollout_policy = ContractRolloutPolicy(
            contract_ref="pubmed/publication",
            active_version="2.0.0",
            mode="dual_write",
            read_order=("2.0.0", "1.0.0"),
            write_versions=("1.0.0", "2.0.0"),
        )
        logger = MagicMock()
        logger.bind = MagicMock(return_value=logger)
        writer = _build_gold_writer(
            base_path="s3://test-bucket/gold",
            logger=logger,
            runtime_services=GoldWriterRuntimeServices(
                csv_exporter=None,
                tracing=MagicMock(),
                metrics=None,
                audit=None,
                metadata_writer=MagicMock(),
                metadata_coordinator=None,
                lineage_store=None,
                contract_rollout_policy=rollout_policy,
            ),
        )
        writer._prepare_write_gold = AsyncMock(  # type: ignore[method-assign]
            side_effect=lambda **kwargs: MagicMock(
                table_name=kwargs["table_name"],
                table_path=f"s3://test-bucket/gold/{kwargs['table_name'].replace('.', '/')}",
                validated_mode=MagicMock(value=kwargs["mode"]),
            )
        )
        writer._dispatch_write = AsyncMock(  # type: ignore[method-assign]
            side_effect=[None, RuntimeError("boom")]
        )
        writer._post_write_gold = AsyncMock()  # type: ignore[method-assign]

        with pytest.raises(RuntimeError, match="boom"):
            await writer.write_gold(
                table_name="test.table",
                records=[
                    {
                        "entity_id": "CHEMBL123",
                        "legacy_value": "old",
                        "value": 5.5,
                    }
                ],
                schema=GoldSchemaPolicyByVersion(
                    active_version="2.0.0",
                    policies=(
                        GoldSchemaVersionPolicy(version="1.0.0", schema=legacy_schema),
                        GoldSchemaVersionPolicy(version="2.0.0", schema=strict_schema),
                    ),
                ),
                mode="append",
            )

        logger.error.assert_called_once_with(
            "gold_dual_write_failed",
            logical_table="test.table",
            failed_contract_version="2.0.0",
            failed_target_table="test.table__v2_0_0",
            active_contract_version="2.0.0",
            write_versions=("1.0.0", "2.0.0"),
        )


@pytest.mark.unit
class TestGoldWriterWriteSimple:
    """Tests for simple write operations."""

    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_write_gold_overwrite_mode(
        self, mock_write_deltalake, gold_writer, valid_records, strict_schema
    ):
        """Test write_gold with overwrite mode."""
        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            schema=strict_schema,
            mode="overwrite",
        )

        mock_write_deltalake.assert_called_once()
        call_kwargs = mock_write_deltalake.call_args[1]
        assert call_kwargs["mode"] == "overwrite"
        assert call_kwargs["table_or_uri"] == "s3://test-bucket/gold/test/table"

    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_write_gold_append_mode(
        self, mock_write_deltalake, gold_writer, valid_records, strict_schema
    ):
        """Test write_gold with append mode."""
        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            schema=strict_schema,
            mode="append",
        )

        mock_write_deltalake.assert_called_once()
        call_kwargs = mock_write_deltalake.call_args[1]
        assert call_kwargs["mode"] == "append"

    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_write_gold_with_partitions(
        self, mock_write_deltalake, gold_writer, valid_records, strict_schema
    ):
        """Test write_gold with partition columns."""
        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            schema=strict_schema,
            mode="overwrite",
            partition_cols=["year", "month"],
        )

        mock_write_deltalake.assert_called_once()
        call_kwargs = mock_write_deltalake.call_args[1]
        assert call_kwargs["partition_by"] == ["year", "month"]


@pytest.mark.unit
class TestGoldWriterSCD2:
    """Tests for SCD Type 2 operations."""

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_write_gold_scd2_creates_new_table(
        self,
        mock_write_deltalake,
        mock_delta_table,
        gold_writer,
        valid_records,
        strict_schema,
        fixed_ingestion_ts,
    ):
        """Test SCD2 write creates new table when table doesn't exist."""
        mock_delta_table.side_effect = TableNotFoundError("Not found")

        scd_config = {
            "business_key": "entity_id",
            "version_col": "version",
            "valid_from_col": "valid_from",
            "valid_to_col": "valid_to",
            "current_flag_col": "is_current",
        }

        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            schema=strict_schema,
            mode="scd2",
            scd_config=scd_config,
            ingestion_ts=fixed_ingestion_ts,
        )

        mock_write_deltalake.assert_called_once()
        # Records should have SCD metadata added
        call_kwargs = mock_write_deltalake.call_args[1]
        assert call_kwargs["mode"] == "append"

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    async def test_write_gold_scd2_merge_existing_table(
        self,
        mock_delta_table,
        gold_writer,
        valid_records,
        strict_schema,
        fixed_ingestion_ts,
    ):
        """Test SCD2 write merges into existing table."""
        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_merge = MagicMock()
        mock_table_instance.merge.return_value = mock_merge
        mock_merge.when_matched_update.return_value = mock_merge
        mock_merge.when_not_matched_insert_all.return_value = mock_merge

        scd_config = {
            "business_key": "entity_id",
        }

        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            schema=strict_schema,
            mode="scd2",
            scd_config=scd_config,
            ingestion_ts=fixed_ingestion_ts,
        )

        mock_table_instance.merge.assert_called_once()
        mock_merge.when_matched_update.assert_called_once()
        mock_merge.when_not_matched_insert_all.assert_called_once()

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    async def test_write_gold_scd2_with_list_business_key(
        self, mock_delta_table, gold_writer, fixed_ingestion_ts
    ):
        """Test SCD2 write with list of business keys."""
        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_merge = MagicMock()
        mock_table_instance.merge.return_value = mock_merge
        mock_merge.when_matched_update.return_value = mock_merge
        mock_merge.when_not_matched_insert_all.return_value = mock_merge

        scd_config = {
            "business_key": ["provider", "entity_id"],
        }

        records = [
            {"provider": "chembl", "entity_id": "CHEMBL123", "value": 5.5},
        ]

        # Create schema that matches records
        multi_key_schema = DataFrameSchema(
            {
                "provider": Column(str, nullable=False),
                "entity_id": Column(str, nullable=False),
                "value": Column(float, nullable=False),
            },
            strict=True,
        )

        await gold_writer.write_gold(
            table_name="test.table",
            records=records,
            schema=multi_key_schema,
            mode="scd2",
            scd_config=scd_config,
            ingestion_ts=fixed_ingestion_ts,
        )

        mock_table_instance.merge.assert_called_once()

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    async def test_write_gold_scd2_uses_content_hash_guard_when_available(
        self,
        mock_delta_table,
        gold_writer,
        fixed_ingestion_ts,
    ):
        """SCD2 merge should only close current rows when content changes."""
        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_merge = MagicMock()
        mock_table_instance.merge.return_value = mock_merge
        mock_merge.when_matched_update.return_value = mock_merge
        mock_merge.when_not_matched_insert_all.return_value = mock_merge

        schema = DataFrameSchema(
            {
                "entity_id": Column(str, nullable=False),
                "value": Column(float, nullable=False),
                "content_hash": Column(str, nullable=False),
            },
            strict=True,
        )
        records = [
            {
                "entity_id": "CHEMBL123",
                "value": 5.5,
                "content_hash": "hash-a",
            }
        ]

        await gold_writer.write_gold(
            table_name="test.table",
            records=records,
            schema=schema,
            mode="scd2",
            scd_config={"business_key": "entity_id"},
            ingestion_ts=fixed_ingestion_ts,
        )

        update_kwargs = mock_merge.when_matched_update.call_args.kwargs
        assert "predicate" in update_kwargs
        assert "source.content_hash <> target.content_hash" in str(
            update_kwargs["predicate"]
        )


@pytest.mark.unit
class TestGoldWriterSchemaValidation:
    """Tests for schema validation."""

    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_write_gold_with_valid_schema(
        self, mock_write_deltalake, gold_writer, strict_schema, valid_records
    ):
        """Test write_gold passes with valid schema."""
        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            schema=strict_schema,
            mode="overwrite",
        )

        mock_write_deltalake.assert_called_once()

    async def test_write_gold_schema_validation_failure(
        self, gold_writer, strict_schema
    ):
        """Test write_gold raises ValueError for invalid records."""
        invalid_records = [
            {"entity_id": "CHEMBL123"},  # Missing 'value'
        ]

        with pytest.raises(ValueError, match="Schema validation failed"):
            await gold_writer.write_gold(
                table_name="test.table",
                records=invalid_records,
                schema=strict_schema,
                mode="overwrite",
            )


@pytest.mark.unit
class TestGoldWriterRead:
    """Tests for read operations."""

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    async def test_read_gold_returns_records(self, mock_delta_table, gold_writer):
        """Test read_gold returns records from table."""

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        # Create mock PyArrow table
        mock_arrow_table = pa.table(
            {
                "entity_id": ["CHEMBL123", "CHEMBL456"],
                "value": [5.5, 7.2],
            }
        )
        mock_table_instance.to_pyarrow_table.return_value = mock_arrow_table

        result = await gold_writer.read_gold("test.table", current_only=False)

        assert len(result) == 2
        assert result[0]["entity_id"] == "CHEMBL123"

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    async def test_read_gold_filters_current_only(self, mock_delta_table, gold_writer):
        """Test read_gold filters for current records when is_current column exists."""

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        # Create mock PyArrow table with is_current column
        mock_arrow_table = pa.table(
            {
                "entity_id": ["CHEMBL123", "CHEMBL123"],
                "value": [5.5, 7.2],
                "is_current": [False, True],
            }
        )
        mock_table_instance.to_pyarrow_table.return_value = mock_arrow_table

        result = await gold_writer.read_gold("test.table", current_only=True)

        # Should only return current record
        assert len(result) == 1
        assert result[0]["value"] == pytest.approx(7.2)


@pytest.mark.unit
class TestGoldWriterHistory:
    """Tests for history retrieval."""

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    async def test_get_history_returns_all_versions(
        self, mock_delta_table, gold_writer
    ):
        """Test get_history returns all historical versions."""

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        # Create mock PyArrow table with history
        mock_arrow_table = pa.table(
            {
                "entity_id": ["CHEMBL123", "CHEMBL123", "CHEMBL456"],
                "value": [5.5, 6.0, 7.2],
                "version": [1, 2, 1],
                "valid_from": ["2024-01-01", "2024-02-01", "2024-01-01"],
            }
        )
        mock_table_instance.to_pyarrow_table.return_value = mock_arrow_table

        result = await gold_writer.get_history("test.table", {"entity_id": "CHEMBL123"})

        # Should return both versions of CHEMBL123
        assert len(result) == 2
        assert all(r["entity_id"] == "CHEMBL123" for r in result)

    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    async def test_get_history_with_multiple_keys(self, mock_delta_table, gold_writer):
        """Test get_history with multiple business key values."""

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        mock_arrow_table = pa.table(
            {
                "provider": ["chembl", "chembl", "pubchem"],
                "entity_id": ["123", "123", "123"],
                "value": [5.5, 6.0, 7.2],
            }
        )
        mock_table_instance.to_pyarrow_table.return_value = mock_arrow_table

        result = await gold_writer.get_history(
            "test.table",
            {"provider": "chembl", "entity_id": "123"},
        )

        # Should return only chembl records
        assert len(result) == 2
        assert all(r["provider"] == "chembl" for r in result)


@pytest.mark.unit
class TestGoldWriterTypeSanitization:
    """Tests for type sanitization methods.

    Note: The _sanitize_type_for_delta method has been extracted to
    ArrowDataConverter. These tests now use the converter directly.
    """

    @pytest.fixture
    def arrow_converter(self):
        """Create an ArrowDataConverter instance for testing."""
        from bioetl.infrastructure.storage.delta.arrow_converter import (
            ArrowDataConverter,
        )

        return ArrowDataConverter()

    def test_sanitize_null_type(self, arrow_converter):
        """Test sanitization of null type to string."""

        result = arrow_converter.sanitize_type_for_delta(pa.null())
        assert result == pa.string()

    def test_sanitize_list_with_null_inner(self, arrow_converter):
        """Test sanitization of list<null> to list<string>."""

        null_list_type = pa.list_(pa.null())
        result = arrow_converter.sanitize_type_for_delta(null_list_type)
        assert result == pa.list_(pa.string())

    def test_sanitize_large_list_type(self, arrow_converter):
        """Test sanitization of large_list type."""

        large_list_type = pa.large_list(pa.null())
        result = arrow_converter.sanitize_type_for_delta(large_list_type)
        assert result == pa.large_list(pa.string())

    def test_sanitize_struct_with_null_field(self, arrow_converter):
        """Test sanitization of struct with null field."""

        struct_type = pa.struct(
            [pa.field("name", pa.string()), pa.field("value", pa.null())]
        )
        result = arrow_converter.sanitize_type_for_delta(struct_type)

        # Check the value field is now string
        assert result[1].type == pa.string()

    def test_sanitize_map_type(self, arrow_converter):
        """Test sanitization of map type."""

        map_type = pa.map_(pa.string(), pa.null())
        result = arrow_converter.sanitize_type_for_delta(map_type)
        assert result.item_type == pa.string()

    def test_sanitize_non_null_type_unchanged(self, arrow_converter):
        """Test that non-null types are unchanged."""

        int_type = pa.int64()
        result = arrow_converter.sanitize_type_for_delta(int_type)
        assert result == pa.int64()


@pytest.mark.unit
class TestGoldWriterToArrowTable:
    """Tests for _to_arrow_table method."""

    def test_to_arrow_table_with_null_columns(self, gold_writer):
        """Test conversion when records have all-null columns."""
        records = [
            {"id": "a", "value": None},
            {"id": "b", "value": None},
        ]

        result = gold_writer._to_arrow_table(records)

        # Value column should be converted to string (or valid type)
        assert result.num_rows == 2

    def test_to_arrow_table_with_mixed_types(self, gold_writer):
        """Test conversion with various data types."""
        records = [
            {"id": "a", "count": 1, "score": 1.5, "active": True},
        ]

        result = gold_writer._to_arrow_table(records)

        assert result.num_rows == 1


@pytest.mark.unit
class TestGoldWriterDeterministicBackoff:
    """Tests for deterministic backoff behavior (ADR-014)."""

    @patch("bioetl.infrastructure.storage.gold_writer.asyncio.sleep")
    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_gold_writer_deterministic_backoff(
        self,
        mock_write_deltalake,
        mock_sleep,
        gold_writer,
        valid_records,
        strict_schema,
    ):
        """Test that backoff uses fixed delay (0.05s jitter) instead of random.

        Verifies REQ-DETERM-001: GoldWriter must use deterministic backoff
        for reproducible retry behavior. The delay formula is:
        delay = 0.5 * (2 ** attempt) + 0.05

        For attempt 0: 0.5 * 1 + 0.05 = 0.55s
        For attempt 1: 0.5 * 2 + 0.05 = 1.05s
        """
        # Simulate failure on first two attempts, success on third
        mock_write_deltalake.side_effect = [
            RuntimeError("Transient error 1"),
            RuntimeError("Transient error 2"),
            None,  # Success on third attempt
        ]

        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            schema=strict_schema,
            mode="overwrite",
        )

        # Verify deterministic backoff delays were used
        assert mock_sleep.call_count == 2
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]

        # Attempt 0: 0.5 * (2**0) + 0.05 = 0.55
        assert sleep_calls[0] == pytest.approx(0.55)
        # Attempt 1: 0.5 * (2**1) + 0.05 = 1.05
        assert sleep_calls[1] == pytest.approx(1.05)

    @patch("bioetl.infrastructure.storage.gold_writer.asyncio.sleep")
    @patch("bioetl.infrastructure.storage.gold_writer.DeltaTable")
    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_gold_writer_scd2_deterministic_backoff(
        self,
        mock_write_deltalake,
        mock_delta_table,
        mock_sleep,
        gold_writer,
        valid_records,
        strict_schema,
        fixed_ingestion_ts,
    ):
        """Test that SCD2 mode also uses deterministic backoff.

        SCD2 writes should use the same deterministic backoff formula
        as simple writes for consistency.
        """
        # Simulate table not found, then transient errors
        mock_delta_table.side_effect = TableNotFoundError("Not found")
        mock_write_deltalake.side_effect = [
            RuntimeError("Transient error 1"),
            RuntimeError("Transient error 2"),
            None,  # Success on third attempt
        ]

        scd_config = {
            "business_key": "entity_id",
            "version_col": "version",
            "valid_from_col": "valid_from",
            "valid_to_col": "valid_to",
            "current_flag_col": "is_current",
        }

        await gold_writer.write_gold(
            table_name="test.table",
            records=valid_records,
            schema=strict_schema,
            mode="scd2",
            scd_config=scd_config,
            ingestion_ts=fixed_ingestion_ts,
        )

        # Verify deterministic backoff delays
        assert mock_sleep.call_count == 2
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls[0] == pytest.approx(0.55)
        assert sleep_calls[1] == pytest.approx(1.05)


@pytest.mark.unit
class TestGoldWriterAudit:
    """Tests for GoldWriter audit logging."""

    async def test_post_write_gold_uses_named_context(
        self, gold_writer, valid_records, strict_schema, fixed_ingestion_ts
    ):
        """Test _post_write_gold consumes a named post-write context."""
        from uuid import uuid4

        from bioetl.domain.types import RunID
        from bioetl.infrastructure.storage.gold_writer import (
            GoldWriteMode,
            _GoldWritePostwriteContext,
            _PreparedGoldWriteContext,
        )

        gold_writer._audit = AsyncMock()
        gold_writer._write_gold_metadata = AsyncMock()  # type: ignore[method-assign]

        context = _GoldWritePostwriteContext(
            prepared=_PreparedGoldWriteContext(
                table_name="test.table",
                table_path="s3://test-bucket/gold/test/table",
                validated_mode=GoldWriteMode.APPEND,
            ),
            records=valid_records,
            ingestion_ts=fixed_ingestion_ts,
            run_id=RunID(uuid4()),
            scd_config=None,
            silver_refs=None,
            schema=strict_schema,
        )

        await gold_writer._post_write_gold(context)

        gold_writer._audit.log_write.assert_called_once()
        gold_writer._write_gold_metadata.assert_awaited_once_with(
            table_path="s3://test-bucket/gold/test/table",
            table_name="test.table",
            records=valid_records,
            mode=GoldWriteMode.APPEND,
            scd_config=None,
            ingestion_ts=fixed_ingestion_ts,
            run_id=context.run_id,
            silver_refs=None,
            gold_schema=strict_schema,
        )

    @pytest.mark.asyncio
    async def test_log_gold_audit_requires_ingestion_ts(
        self, gold_writer, valid_records
    ):
        """Test _log_gold_audit raises ValueError when ingestion_ts is None."""
        from bioetl.domain.medallion import GoldWriteMode

        with pytest.raises(ValueError, match="ingestion_ts is required"):
            await gold_writer._log_gold_audit(
                table_name="test.table",
                records=valid_records,
                mode=GoldWriteMode.OVERWRITE,
                ingestion_ts=None,
                run_id=None,
            )

    @pytest.mark.asyncio
    async def test_log_gold_audit_requires_run_id(
        self, gold_writer, valid_records, fixed_ingestion_ts
    ):
        """Test _log_gold_audit raises when run_id is not provided."""
        from unittest.mock import AsyncMock

        from bioetl.domain.medallion import GoldWriteMode

        mock_audit = AsyncMock()
        gold_writer._audit = mock_audit

        with pytest.raises(ValueError, match="run_id is required"):
            await gold_writer._log_gold_audit(
                table_name="test.table",
                records=valid_records,
                mode=GoldWriteMode.OVERWRITE,
                ingestion_ts=fixed_ingestion_ts,
                run_id=None,
            )

        mock_audit.log_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_gold_audit_with_valid_data(
        self, gold_writer, valid_records, fixed_ingestion_ts
    ):
        """Test _log_gold_audit logs correctly with valid data."""
        from unittest.mock import AsyncMock
        from uuid import uuid4

        from bioetl.domain.medallion import GoldWriteMode
        from bioetl.domain.types import RunID

        mock_audit = AsyncMock()
        gold_writer._audit = mock_audit

        run_id = RunID(uuid4())
        await gold_writer._log_gold_audit(
            table_name="test.table",
            records=valid_records,
            mode=GoldWriteMode.APPEND,
            ingestion_ts=fixed_ingestion_ts,
            run_id=run_id,
        )

        mock_audit.log_write.assert_called_once()
        call_args = mock_audit.log_write.call_args
        audit_entry = call_args[0][0]

        assert audit_entry.run_id == run_id
        assert audit_entry.records_count == len(valid_records)
        assert audit_entry.metadata["write_mode"] == "append"

    @pytest.mark.asyncio
    async def test_log_gold_audit_scd2_mode_maps_to_merge(
        self, gold_writer, valid_records, fixed_ingestion_ts
    ):
        """Test _log_gold_audit maps SCD2 mode to MERGE operation."""
        from unittest.mock import AsyncMock
        from uuid import uuid4

        from bioetl.domain.medallion import GoldWriteMode
        from bioetl.domain.ports.audit import AuditOperation
        from bioetl.domain.types import RunID

        mock_audit = AsyncMock()
        gold_writer._audit = mock_audit

        run_id = RunID(uuid4())
        await gold_writer._log_gold_audit(
            table_name="test.table",
            records=valid_records,
            mode=GoldWriteMode.SCD2,
            ingestion_ts=fixed_ingestion_ts,
            run_id=run_id,
        )

        mock_audit.log_write.assert_called_once()
        call_args = mock_audit.log_write.call_args
        audit_entry = call_args[0][0]

        # SCD2 should map to MERGE operation
        assert audit_entry.operation == AuditOperation.MERGE


@pytest.mark.unit
class TestGoldWriterArrowConversion:
    """Tests for GoldWriter Arrow table conversion."""

    def test_to_arrow_table_handles_null_type(self, gold_writer):
        """Test _to_arrow_table converts null types to string."""
        records = [
            {"id": "1", "null_field": None},
            {"id": "2", "null_field": None},
        ]

        result = gold_writer._to_arrow_table(records)

        # Should have converted successfully
        assert len(result) == 2
        assert "null_field" in result.column_names

    def test_to_arrow_table_sorts_columns(self, gold_writer):
        """Test _to_arrow_table enforces deterministic column order."""
        records = [
            {"z_field": 1, "a_field": 2, "m_field": 3},
        ]

        result = gold_writer._to_arrow_table(records)

        # Columns should be sorted alphabetically
        assert result.column_names == ["a_field", "m_field", "z_field"]

    def test_sanitize_type_for_delta_null_type(self):
        """Test sanitize_type_for_delta converts null to string."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.delta.arrow_converter import (
            ArrowDataConverter,
        )

        converter = ArrowDataConverter()
        result = converter.sanitize_type_for_delta(pa.null())
        assert result == pa.string()

    def test_sanitize_type_for_delta_list_with_null(self):
        """Test sanitize_type_for_delta handles list<null>."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.delta.arrow_converter import (
            ArrowDataConverter,
        )

        converter = ArrowDataConverter()
        result = converter.sanitize_type_for_delta(pa.list_(pa.null()))
        assert result == pa.list_(pa.string())

    def test_sanitize_type_for_delta_struct_with_null(self):
        """Test sanitize_type_for_delta handles struct with null field."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.delta.arrow_converter import (
            ArrowDataConverter,
        )

        converter = ArrowDataConverter()
        struct_type = pa.struct([pa.field("null_field", pa.null())])
        result = converter.sanitize_type_for_delta(struct_type)

        expected = pa.struct([pa.field("null_field", pa.string())])
        assert result == expected

    def test_sanitize_type_for_delta_preserves_normal_types(self):
        """Test sanitize_type_for_delta preserves non-null types."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.delta.arrow_converter import (
            ArrowDataConverter,
        )

        converter = ArrowDataConverter()
        # Test various normal types
        for dtype in [pa.int64(), pa.float64(), pa.string(), pa.bool_()]:
            result = converter.sanitize_type_for_delta(dtype)
            assert result == dtype

    def test_sanitize_type_for_delta_map_type(self):
        """Test sanitize_type_for_delta handles map types."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.delta.arrow_converter import (
            ArrowDataConverter,
        )

        converter = ArrowDataConverter()
        map_type = pa.map_(pa.string(), pa.null())
        result = converter.sanitize_type_for_delta(map_type)

        expected = pa.map_(pa.string(), pa.string())
        assert result == expected


@pytest.mark.unit
class TestGoldWriterMergedValidation:
    """Tests for write_gold_merged schema validation (REQ-DATA-009)."""

    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_write_gold_merged_with_strict_schema_passes(
        self, mock_write_deltalake, gold_writer, strict_schema, valid_records
    ):
        """Test write_gold_merged passes validation with strict schema."""
        await gold_writer.write_gold_merged(
            table_name="test.merged_table",
            records=valid_records,
            schema=strict_schema,
        )

        mock_write_deltalake.assert_called_once()

    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_write_gold_merged_non_strict_schema_rejected(
        self, mock_write_deltalake, gold_writer, non_strict_schema, valid_records
    ):
        """write_gold_merged rejects non-strict schemas."""
        with pytest.raises(ValueError, match="strict=True"):
            await gold_writer.write_gold_merged(
                table_name="test.merged_table",
                records=valid_records,
                schema=non_strict_schema,
            )
        mock_write_deltalake.assert_not_called()

    async def test_write_gold_merged_schema_validation_failure(
        self, gold_writer, strict_schema
    ):
        """Test write_gold_merged rejects records that fail schema validation."""
        invalid_records = [
            {"entity_id": "CHEMBL123"},  # Missing 'value' required by strict schema
        ]

        with pytest.raises(ValueError, match="Schema validation failed"):
            await gold_writer.write_gold_merged(
                table_name="test.merged_table",
                records=invalid_records,
                schema=strict_schema,
            )

    @patch("bioetl.infrastructure.storage.gold_writer.write_deltalake")
    async def test_write_gold_merged_without_schema_fails_fast(
        self, mock_write_deltalake, gold_writer, valid_records
    ):
        """Merged Gold writes require a registered strict schema."""
        with pytest.raises(ValueError, match="require a registered strict schema"):
            await gold_writer.write_gold_merged(
                table_name="test.merged_table",
                records=valid_records,
            )

        mock_write_deltalake.assert_not_called()

    async def test_write_gold_merged_rejects_non_strict_schema(
        self, gold_writer, valid_records
    ):
        """Merged Gold writes reject schemas that do not enforce strict mode."""
        import pandera.pandas as pa
        from pandera.typing import Series

        class NonStrictSchema(pa.DataFrameModel):
            entity_id: Series[str] = pa.Field(nullable=False)

            class Config:
                strict = False

        with pytest.raises(ValueError, match="strict=True"):
            await gold_writer.write_gold_merged(
                table_name="test.merged_table",
                records=valid_records,
                schema=NonStrictSchema,
            )

    async def test_write_gold_merged_empty_records_returns(
        self, gold_writer, strict_schema
    ):
        """Test write_gold_merged returns early for empty records."""
        # Should not raise, just return silently
        await gold_writer.write_gold_merged(
            table_name="test.merged_table",
            records=[],
            schema=strict_schema,
        )
