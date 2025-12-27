"""Architecture test: Medallion layer invariants.

REQ-LINEAGE-001: Bronze metadata for data lineage tracking.
Bronze layer MUST include metadata fields for traceability.

See docs/02-architecture/decisions/ADR-014-deterministic-writes.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Path relative to project root
BRONZE_WRITER_PATH = Path("src/bioetl/infrastructure/storage/bronze_writer.py")


class TestBronzeMetadataInvariants:
    """Tests ensuring Bronze writer includes required metadata fields."""

    @pytest.fixture
    def bronze_writer_source(self) -> str:
        """Get Bronze writer source code."""
        # Handle both running from project root and tests directory
        if BRONZE_WRITER_PATH.exists():
            path = BRONZE_WRITER_PATH
        else:
            path = Path(__file__).parent.parent.parent / BRONZE_WRITER_PATH

        return path.read_text(encoding="utf-8")

    def test_bronze_writer_requires_metadata(self, bronze_writer_source: str) -> None:
        """Bronze writer MUST include metadata fields for lineage tracking.

        These fields are essential for data provenance and audit trail.
        Removing any of them breaks the ability to trace data origins.

        Metadata is stored in separate .meta.json files alongside data.
        """
        # Bronze metadata uses non-prefixed keys in _build_bronze_metadata method
        # These are the canonical field names in Bronze layer
        required_fields = [
            "ingestion_ts",  # When data was ingested (ISO timestamp)
            "run_id",  # Pipeline run identifier
            "run_type",  # Type of run (incremental, backfill, rebuild)
            "batch_id",  # Source batch identifier for traceability
        ]

        missing_fields = []
        for field in required_fields:
            # Check for field as dictionary key in metadata construction
            # Pattern: "field_name": ... in _build_bronze_metadata
            if f'"{field}"' not in bronze_writer_source:
                missing_fields.append(field)

        assert not missing_fields, (
            f"Bronze writer missing required metadata fields: {missing_fields}\n\n"
            "Bronze metadata is essential for data lineage tracking.\n"
            "These fields MUST be present in _build_bronze_metadata():\n"
            "  - ingestion_ts: Timestamp of data ingestion\n"
            "  - run_id: Pipeline run identifier\n"
            "  - run_type: Type of run (incremental/backfill/rebuild)\n"
            "  - batch_id: Source batch identifier\n\n"
            "See REQ-LINEAGE-001 and RULES.md §2.1.1"
        )

    def test_bronze_writer_has_metadata_builder(
        self, bronze_writer_source: str
    ) -> None:
        """Bronze writer MUST have _build_bronze_metadata method.

        This method centralizes metadata construction for consistency.
        """
        assert "_build_bronze_metadata" in bronze_writer_source, (
            "Bronze writer missing _build_bronze_metadata method.\n"
            "Metadata construction must be centralized in this method."
        )

    def test_bronze_writer_writes_metadata_file(
        self, bronze_writer_source: str
    ) -> None:
        """Bronze writer MUST write metadata to separate .meta.json file.

        Metadata is stored alongside data for atomic consistency.
        """
        assert ".meta.json" in bronze_writer_source, (
            "Bronze writer must write metadata to .meta.json files.\n"
            "Metadata files ensure data lineage is preserved with data."
        )

    def test_bronze_writer_validates_timestamps(
        self, bronze_writer_source: str
    ) -> None:
        """Bronze writer MUST validate UTC timestamps.

        Per ADR-014, timestamps must be timezone-aware and in UTC
        for deterministic behavior and lineage consistency.
        """
        assert "_validate_utc_datetime" in bronze_writer_source, (
            "Bronze writer must validate UTC timestamps.\n"
            "Timestamps must be timezone-aware and in UTC per ADR-014."
        )

    def test_bronze_path_includes_date_partition(
        self, bronze_writer_source: str
    ) -> None:
        """Bronze paths MUST include date partitioning.

        Path format: bronze/v1/{provider}/{entity}/{date}/
        """
        # Check for date-based path construction pattern
        assert "bronze/v1/" in bronze_writer_source, (
            "Bronze path must follow format: bronze/v1/{provider}/{entity}/{date}/\n"
            "See RULES.md §2.1.1 - REQ-DATA-002"
        )
