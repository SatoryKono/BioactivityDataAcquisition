"""Tests for TableConfig configuration object.

Tests for TableConfig frozen dataclass with write mode conversions.
"""

from __future__ import annotations

import pytest

from bioetl.domain.config.table import TableConfig
from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode


@pytest.mark.unit
class TestTableConfig:
    """Tests for TableConfig frozen dataclass."""

    def test_table_table_config__default_values__0f8b8c87(self) -> None:
        config = TableConfig()
        assert config.primary_keys == ("entity_id",)
        assert config.silver_table is None
        assert config.gold_table is None
        assert config.silver_write_mode == SilverWriteMode.MERGE
        assert config.gold_write_mode == GoldWriteMode.SCD2
        assert config.silver_idempotency_contract is None
        assert config.gold_idempotency_contract is None
        assert config.partition_cols == ()
        assert config.on_schema_mismatch == "error"

    def test_custom_primary_keys(self) -> None:
        config = TableConfig(primary_keys=("id", "version"))
        assert config.primary_keys == ("id", "version")

    def test_table_table_config__to_tuple_conversion__160b1df7(self) -> None:
        config = TableConfig(primary_keys=["entity_id"])  # type: ignore[arg-type]
        assert isinstance(config.primary_keys, tuple)

    def test_string_write_mode_conversion(self) -> None:
        config = TableConfig(
            silver_write_mode="merge",  # type: ignore[arg-type]
            gold_write_mode="append",  # type: ignore[arg-type]
        )
        assert config.silver_write_mode == SilverWriteMode.MERGE
        assert config.gold_write_mode == GoldWriteMode.APPEND

    def test_enum_write_mode_passthrough(self) -> None:
        config = TableConfig(
            silver_write_mode=SilverWriteMode.MERGE,
            gold_write_mode=GoldWriteMode.SCD2,
        )
        assert config.silver_write_mode == SilverWriteMode.MERGE
        assert config.gold_write_mode == GoldWriteMode.SCD2

    def test_idempotency_contract_normalization(self) -> None:
        config = TableConfig(
            silver_idempotency_contract=" merge_upsert ",  # type: ignore[arg-type]
            gold_idempotency_contract="SCD2",  # type: ignore[arg-type]
        )
        assert config.silver_idempotency_contract == "merge_upsert"
        assert config.gold_idempotency_contract == "scd2"

    def test_invalid_idempotency_contract_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid idempotency contract"):
            TableConfig(
                silver_idempotency_contract="not-a-contract",  # type: ignore[arg-type]
            )

    def test_custom_tables(self) -> None:
        config = TableConfig(
            silver_table="chembl.activity",
            gold_table="chembl.activity_gold",
        )
        assert config.silver_table == "chembl.activity"
        assert config.gold_table == "chembl.activity_gold"

    def test_partition_cols(self) -> None:
        config = TableConfig(partition_cols=("provider", "entity_type"))
        assert config.partition_cols == ("provider", "entity_type")

    def test_schema_mismatch_modes(self) -> None:
        for mode in ("error", "evolve", "ignore"):
            config = TableConfig(on_schema_mismatch=mode)  # type: ignore[arg-type]
            assert config.on_schema_mismatch == mode
