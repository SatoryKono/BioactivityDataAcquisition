"""Unit tests for MetadataBuilder classes.

Tests the metadata building utilities extracted from SilverWriter and GoldWriter.
"""

from __future__ import annotations

import pytest

from bioetl.infrastructure.storage.metadata_builder import (
    GoldMetadataBuilder,
    SilverMetadataBuilder,
    _parse_table_name,
)


class TestParseTableName:
    """Tests for the table name parsing utility."""

    def test_parse_dot_notation(self) -> None:
        """Should parse dot notation: 'chembl.activity' -> ('chembl', 'activity')."""
        provider, entity = _parse_table_name("chembl.activity")
        assert provider == "chembl"
        assert entity == "activity"

    def test_parse_path_notation(self) -> None:
        """Should parse path notation: 'composite/publication' -> ('composite', 'publication')."""
        provider, entity = _parse_table_name("composite/publication")
        assert provider == "composite"
        assert entity == "publication"

    def test_parse_underscore_notation(self) -> None:
        """Should parse underscore notation: 'chembl_activity' -> ('chembl', 'activity')."""
        provider, entity = _parse_table_name("chembl_activity")
        assert provider == "chembl"
        assert entity == "activity"

    def test_parse_plain_name(self) -> None:
        """Should handle plain name: 'activity' -> ('unknown', 'activity')."""
        provider, entity = _parse_table_name("activity")
        assert provider == "unknown"
        assert entity == "activity"

    def test_parse_empty_string(self) -> None:
        """Should handle empty string: '' -> ('unknown', 'unknown')."""
        provider, entity = _parse_table_name("")
        assert provider == "unknown"
        assert entity == "unknown"

    def test_parse_multiple_dots(self) -> None:
        """Should handle multiple dots: 'a.b.c' -> ('a', 'b')."""
        provider, entity = _parse_table_name("a.b.c")
        assert provider == "a"
        assert entity == "b"

    def test_parse_single_slash(self) -> None:
        """Should handle path with single component: '/entity' -> ('composite', 'entity')."""
        provider, entity = _parse_table_name("/entity")
        assert provider == ""  # Empty string before slash
        assert entity == "entity"


class TestSilverMetadataBuilder:
    """Tests for SilverMetadataBuilder."""

    def test_build_merged_metadata_basic(self) -> None:
        """Should build valid SilverMetadata for merged composite data."""
        builder = SilverMetadataBuilder()
        records = [
            {"id": 1, "name": "test1"},
            {"id": 2, "name": "test2"},
        ]
        metadata = builder.build_merged_metadata(
            table_path="/data/silver/composite/publication",
            table_name="composite/publication",
            records=records,
            primary_keys=["id"],
            run_id="run-123",
            sources_used=["seed", "crossref"],
        )

        assert metadata.runtime.run_id == "run-123"
        assert metadata.pipeline.name == "composite_publication"
        assert metadata.pipeline.provider == "composite"
        assert metadata.pipeline.entity == "publication"
        assert metadata.delta.table_path == "/data/silver/composite/publication"
        assert metadata.delta.rows_inserted == 2
        assert metadata.dq_summary.total_records == 2
        assert metadata.output.record_count == 2

    def test_build_merged_metadata_with_transform_version(self) -> None:
        """Should use custom transform version."""
        builder = SilverMetadataBuilder(
            transform_version="2.0.0",
            transform_steps=("normalize", "validate", "merge"),
        )
        records = [{"id": 1}]
        metadata = builder.build_merged_metadata(
            table_path="/data/silver/test",
            table_name="test.entity",
            records=records,
            primary_keys=["id"],
        )

        assert metadata.lineage.transform_version == "2.0.0"
        assert metadata.lineage.transform_steps == ["normalize", "validate", "merge"]

    def test_build_merged_metadata_empty_records(self) -> None:
        """Should handle empty record list."""
        builder = SilverMetadataBuilder()
        metadata = builder.build_merged_metadata(
            table_path="/data/silver/test",
            table_name="test.entity",
            records=[],
            primary_keys=["id"],
        )

        assert metadata.delta.rows_inserted == 0
        assert metadata.dq_summary.total_records == 0
        assert metadata.output.record_count == 0


class TestGoldMetadataBuilder:
    """Tests for GoldMetadataBuilder."""

    def test_build_fallback_metadata_basic(self) -> None:
        """Should build valid GoldMetadata using fallback logic."""
        from bioetl.domain.medallion import GoldWriteMode

        builder = GoldMetadataBuilder()
        records = [{"id": 1, "value": 100}]
        metadata = builder.build_fallback_metadata(
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
        )

        assert metadata.pipeline.name == "chembl_activity"
        assert metadata.pipeline.provider == "chembl"
        assert metadata.pipeline.entity == "activity"
        assert metadata.dq_summary.total_records == 1
        assert metadata.output.record_count == 1
        assert metadata.scd is None  # No SCD for OVERWRITE mode

    def test_build_fallback_metadata_scd2_mode(self) -> None:
        """Should include SCD metadata for SCD2 mode."""
        from bioetl.domain.medallion import GoldWriteMode

        builder = GoldMetadataBuilder()
        records = [{"id": 1}]
        scd_config = {
            "valid_from_col": "effective_date",
            "valid_to_col": "end_date",
            "current_flag_col": "is_active",
        }
        metadata = builder.build_fallback_metadata(
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.SCD2,
            scd_config=scd_config,
        )

        assert metadata.scd is not None
        assert metadata.scd.enabled is True
        assert metadata.scd.effective_date_column == "effective_date"
        assert metadata.scd.end_date_column == "end_date"
        assert metadata.scd.current_flag_column == "is_active"

    def test_build_merged_metadata_basic(self) -> None:
        """Should build valid GoldMetadata for merged composite data."""
        builder = GoldMetadataBuilder()
        records = [
            {
                "id": 1,
                "name": "test1",
                "_composite_run_id": "run-456",
                "_source_providers": "['seed', 'openalex']",
                "_enrichment_status": "{'openalex': 'ok'}",
                "_lineage_created_at": "2026-01-01T10:00:00+00:00",
            },
            {"id": 2, "name": "test2"},
        ]
        metadata = builder.build_merged_metadata(
            table_path="/data/gold/composite/publication",
            table_name="composite/publication",
            records=records,
            primary_keys=["id"],
            run_id="run-456",
            sources_used=["seed", "openalex"],
        )

        assert metadata.runtime.run_id == "run-456"
        assert metadata.pipeline.name == "composite_publication"
        assert metadata.pipeline.provider == "composite"
        assert metadata.pipeline.entity == "publication"
        assert metadata.output.record_count == 2
        assert metadata.output.composite_run_id == "run-456"
        assert metadata.output_ext.composite_run_id == "run-456"
        assert metadata.output_ext.source_providers == ["seed", "openalex"]
        assert metadata.output_ext.enrichment_status == {"openalex": "ok"}

    def test_build_merged_metadata_with_transform_steps(self) -> None:
        """Should use custom transform steps."""
        builder = GoldMetadataBuilder(
            transform_version="1.5.0",
            transform_steps=("filter", "aggregate"),
        )
        records = [{"id": 1}]
        metadata = builder.build_merged_metadata(
            table_path="/data/gold/test",
            table_name="test.entity",
            records=records,
            primary_keys=["id"],
        )

        assert metadata.lineage.transform_version == "1.5.0"
        assert metadata.lineage.transform_steps == ["filter", "aggregate"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
