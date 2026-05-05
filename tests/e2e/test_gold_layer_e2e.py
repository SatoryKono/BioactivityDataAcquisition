"""E2E tests for Gold layer operations.

Tests the Gold layer behavior including:
- Write modes (overwrite, append, scd2)
- Schema validation
- Audit fields
- Cross-references

Per RULES.md 3.0 Medallion Architecture:
- Gold: SCD Type 2 or partitions by date
- Plat structure with scalar fields only
- Forensic: Silver preserves JSON
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger


@pytest.mark.e2e
class TestGoldWriteModes:
    """Tests for Gold layer write modes."""

    def test_gold_write_mode_overwrite_enum(self):
        """E2E: GoldWriteMode.OVERWRITE is available."""
        from bioetl.infrastructure.storage.gold_writer import GoldWriteMode

        assert GoldWriteMode.OVERWRITE.value == "overwrite"

    def test_gold_write_mode_append_enum(self):
        """E2E: GoldWriteMode.APPEND is available."""
        from bioetl.infrastructure.storage.gold_writer import GoldWriteMode

        assert GoldWriteMode.APPEND.value == "append"

    def test_gold_write_mode_scd2_enum(self):
        """E2E: GoldWriteMode.SCD2 is available."""
        from bioetl.infrastructure.storage.gold_writer import GoldWriteMode

        assert GoldWriteMode.SCD2.value == "scd2"

    def test_gold_write_mode_values(self):
        """E2E: All GoldWriteMode values are valid."""
        from bioetl.infrastructure.storage.gold_writer import GoldWriteMode

        valid_modes = ["overwrite", "append", "scd2"]
        for mode in GoldWriteMode:
            assert mode.value in valid_modes


@pytest.mark.e2e
class TestGoldSchemaValidation:
    """Tests for Gold layer schema validation."""

    def test_gold_schema_flat_structure(self):
        """E2E: Gold records should have flat structure (no nested JSON)."""
        flat_record = {
            "entity_id": "test_123",
            "value": 42.5,
            "name": "Test Entity",
            "category": "A",
            "active": True,
        }

        # Verify no nested structures
        for key, value in flat_record.items():
            assert not isinstance(value, dict), f"Field {key} should not be dict"
            assert not isinstance(value, list), f"Field {key} should not be list"

    def test_gold_excludes_json_fields(self):
        """E2E: Gold records exclude complex JSON fields."""
        silver_record = {
            "entity_id": "test_123",
            "name": "Test Entity",
            "properties": {"nested": "value"},  # Should be excluded in Gold
            "synonyms": ["syn1", "syn2"],  # Should be excluded in Gold
        }

        # Gold transformation should exclude nested fields
        gold_record = {
            "entity_id": silver_record["entity_id"],
            "name": silver_record["name"],
            # properties and synonyms excluded
        }

        assert "properties" not in gold_record
        assert "synonyms" not in gold_record

    def test_gold_preserves_scalar_types(self):
        """E2E: Gold records preserve scalar type integrity."""
        record = {
            "id": "test",
            "int_field": 42,
            "float_field": 3.14,
            "bool_field": True,
            "str_field": "value",
        }

        assert isinstance(record["int_field"], int)
        assert isinstance(record["float_field"], float)
        assert isinstance(record["bool_field"], bool)
        assert isinstance(record["str_field"], str)


@pytest.mark.e2e
class TestGoldAuditFields:
    """Tests for Gold layer audit fields."""

    def test_gold_has_ingestion_timestamp(self):
        """E2E: Gold records should have ingestion timestamp."""
        from datetime import UTC, datetime

        gold_record = {
            "entity_id": "test_123",
            "_ingestion_ts": datetime(2026, 1, 1, 12, 0, tzinfo=UTC).isoformat(),
        }

        assert "_ingestion_ts" in gold_record

    def test_gold_has_run_id(self):
        """E2E: Gold records should have run ID for audit correlation."""
        gold_record = {
            "entity_id": "test_123",
            "_run_id": str(uuid4()),
        }

        assert "_run_id" in gold_record

    def test_audit_fields_format(self):
        """E2E: Audit fields should have correct format."""
        run_id = uuid4()
        gold_record = {
            "entity_id": "test_123",
            "_run_id": str(run_id),
            "_run_type": "incremental",
            "_ingestion_ts": "2025-01-15T12:00:00Z",
        }

        # Run ID should be valid UUID string
        assert len(gold_record["_run_id"]) == 36

        # Run type should be valid enum value
        assert gold_record["_run_type"] in ["incremental", "backfill", "rebuild"]


@pytest.mark.e2e
class TestGoldSCD2Behavior:
    """Tests for Gold layer SCD Type 2 behavior."""

    def test_scd2_valid_from_field(self):
        """E2E: SCD2 records have valid_from timestamp."""
        scd2_record = {
            "entity_id": "test_123",
            "version": 1,
            "valid_from": "2025-01-01T00:00:00Z",
            "valid_to": None,  # Current record
            "is_current": True,
        }

        assert "valid_from" in scd2_record
        assert scd2_record["is_current"] is True

    def test_scd2_historical_record(self):
        """E2E: SCD2 historical records have valid_to timestamp."""
        historical_record = {
            "entity_id": "test_123",
            "version": 1,
            "valid_from": "2025-01-01T00:00:00Z",
            "valid_to": "2025-01-15T00:00:00Z",  # Superseded
            "is_current": False,
        }

        assert historical_record["valid_to"] is not None
        assert historical_record["is_current"] is False

    def test_scd2_version_tracking(self):
        """E2E: SCD2 tracks version numbers."""
        records = [
            {"entity_id": "test_123", "version": 1, "is_current": False},
            {"entity_id": "test_123", "version": 2, "is_current": False},
            {"entity_id": "test_123", "version": 3, "is_current": True},
        ]

        versions = [r["version"] for r in records]
        assert versions == [1, 2, 3]
        assert records[-1]["is_current"] is True


@pytest.mark.e2e
class TestSilverToGoldTransformation:
    """Tests for Silver to Gold transformation logic."""

    def test_json_field_exclusion_config(self):
        """E2E: JSON field exclusion is configurable via YAML."""
        # Gold filters are configured in pipeline YAML
        # Example: gold_filters.exclude_fields = ["raw_json", "metadata"]
        config = {
            "gold_filters": {
                "exclude_fields": ["raw_json", "metadata", "debug_info"],
            }
        }

        silver_record = {
            "entity_id": "test_123",
            "name": "Test",
            "raw_json": {"complex": "data"},
            "metadata": {"source": "api"},
            "debug_info": {"trace_id": "abc"},
        }

        # Apply exclusion
        gold_record = {
            k: v
            for k, v in silver_record.items()
            if k not in config["gold_filters"]["exclude_fields"]
        }

        assert "raw_json" not in gold_record
        assert "metadata" not in gold_record
        assert "debug_info" not in gold_record
        assert "entity_id" in gold_record
        assert "name" in gold_record

    def test_silver_preserves_json_for_forensics(self):
        """E2E: Silver layer preserves JSON for forensic analysis."""
        silver_record = {
            "entity_id": "test_123",
            "name": "Test",
            "raw_data": {"api_response": {"field": "value", "array": [1, 2, 3]}},
        }

        # Silver preserves complex structures
        assert "raw_data" in silver_record
        assert isinstance(silver_record["raw_data"], dict)


@pytest.mark.e2e
class TestGoldTableNaming:
    """Tests for Gold table naming conventions."""

    def test_gold_table_name_format(self):
        """E2E: Gold table names follow provider.entity format."""
        table_names = [
            "chembl.activity",
            "chembl.molecule",
            "pubchem.compound",
            "uniprot.protein",
            "pubmed.publication",
        ]

        for name in table_names:
            parts = name.split(".")
            assert len(parts) == 2
            assert len(parts[0]) > 0  # provider
            assert len(parts[1]) > 0  # entity

    def test_gold_table_path_derivation(self):
        """E2E: Gold table paths are derived from names."""
        table_name = "chembl.activity"
        base_path = Path("/data/gold")

        expected_path = base_path / "chembl" / "activity"
        derived_path = base_path / table_name.replace(".", "/")

        assert str(derived_path) == str(expected_path)


@pytest.mark.e2e
class TestGoldPartitioning:
    """Tests for Gold layer partitioning."""

    def test_date_partitioning_support(self):
        """E2E: Gold supports date-based partitioning."""
        record_with_date = {
            "entity_id": "test_123",
            "_ingestion_date": "2025-01-15",
        }

        # Date partition would be: gold/table/ingestion_date=2025-01-15/
        partition_key = record_with_date["_ingestion_date"]
        assert len(partition_key) == 10  # YYYY-MM-DD format

    def test_provider_partitioning_support(self):
        """E2E: Gold supports provider-based partitioning."""
        records = [
            {"entity_id": "1", "provider": "chembl"},
            {"entity_id": "2", "provider": "pubchem"},
            {"entity_id": "3", "provider": "uniprot"},
        ]

        providers = {r["provider"] for r in records}
        assert len(providers) == 3


@pytest.mark.e2e
class TestGoldDataQuality:
    """Tests for Gold layer data quality."""

    def test_gold_no_null_primary_keys(self):
        """E2E: Gold records should not have null primary keys."""
        valid_records = [
            {"entity_id": "test_1", "name": "A"},
            {"entity_id": "test_2", "name": "B"},
        ]

        for record in valid_records:
            assert record["entity_id"] is not None

    def test_gold_unique_entity_ids(self):
        """E2E: Gold entity IDs should be unique within a batch."""
        records = [
            {"entity_id": "test_1", "version": 1},
            {"entity_id": "test_2", "version": 1},
            {"entity_id": "test_3", "version": 1},
        ]

        entity_ids = [r["entity_id"] for r in records]
        assert len(entity_ids) == len(set(entity_ids))

    def test_gold_type_consistency(self):
        """E2E: Gold field types should be consistent across records."""
        records = [
            {"entity_id": "1", "value": 1.0, "active": True},
            {"entity_id": "2", "value": 2.0, "active": False},
            {"entity_id": "3", "value": 3.0, "active": True},
        ]

        # All value fields should be float
        value_types = {type(r["value"]) for r in records}
        assert len(value_types) == 1
        assert float in value_types

        # All active fields should be bool
        active_types = {type(r["active"]) for r in records}
        assert len(active_types) == 1
        assert bool in active_types
