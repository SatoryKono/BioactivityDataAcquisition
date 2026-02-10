"""Silver Schema Stability Tests.

Contract tests that ensure Silver schemas don't change accidentally.
Uses snapshot testing to detect any field additions, deletions, or type changes.

To update snapshots after intentional schema changes:
    UPDATE_SNAPSHOTS=1 pytest tests/contract/silver_schemas/test_schema_stability.py

Related:
    - RULES.md §2.1: Medallion Architecture
    - ADR-018: Gold Strict Validation
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.contract.silver_schemas.conftest import (
    SILVER_SCHEMAS,
    extract_field_metadata,
    load_snapshot,
    save_snapshot,
)

UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"


@pytest.mark.contracts
@pytest.mark.no_api
@pytest.mark.no_api
class TestSchemaStability:
    """Snapshot tests for Silver schema field structure."""

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_schema_fields_unchanged(
        self, schema_name: str, snapshots_dir: Path
    ) -> None:
        """Silver schema fields MUST NOT change without explicit snapshot update.

        This test prevents accidental schema modifications that would break
        downstream consumers and Gold layer contracts.

        If schema change is intentional:
            UPDATE_SNAPSHOTS=1 pytest tests/contract/silver_schemas/test_schema_stability.py
        """
        schema_class = SILVER_SCHEMAS[schema_name]

        # Extract current schema metadata
        current_metadata = extract_field_metadata(schema_class)

        # Load existing snapshot
        snapshot = load_snapshot(schema_name, snapshots_dir)

        if snapshot is None or UPDATE_SNAPSHOTS:
            # Create or update snapshot
            save_snapshot(schema_name, current_metadata, snapshots_dir)
            if snapshot is None:
                pytest.skip(f"Created initial snapshot for {schema_name}")
            else:
                pytest.skip(f"Updated snapshot for {schema_name} (UPDATE_SNAPSHOTS=1)")

        # Compare current schema with snapshot
        current_fields = set(current_metadata.keys())
        snapshot_fields = set(snapshot.keys())

        # Check for added fields
        added_fields = current_fields - snapshot_fields
        if added_fields:
            pytest.fail(
                f"{schema_name}: New fields detected: {sorted(added_fields)}\n"
                "If intentional, run: UPDATE_SNAPSHOTS=1 pytest ..."
            )

        # Check for removed fields
        removed_fields = snapshot_fields - current_fields
        if removed_fields:
            pytest.fail(
                f"{schema_name}: Fields removed: {sorted(removed_fields)}\n"
                "This is a BREAKING CHANGE. Update downstream consumers first.\n"
                "Then run: UPDATE_SNAPSHOTS=1 pytest ..."
            )

        # Check for field metadata changes (type, nullable, checks)
        for field_name in current_fields:
            current_field = current_metadata[field_name]
            snapshot_field = snapshot[field_name]

            # Compare field attributes
            for attr in ["dtype", "nullable", "required"]:
                if current_field.get(attr) != snapshot_field.get(attr):
                    pytest.fail(
                        f"{schema_name}.{field_name}: {attr} changed\n"
                        f"  Expected: {snapshot_field.get(attr)}\n"
                        f"  Got:      {current_field.get(attr)}\n"
                        "If intentional, run: UPDATE_SNAPSHOTS=1 pytest ..."
                    )

            # Compare validation checks
            current_checks = {c["name"] for c in current_field.get("checks", [])}
            snapshot_checks = {c["name"] for c in snapshot_field.get("checks", [])}

            added_checks = current_checks - snapshot_checks
            removed_checks = snapshot_checks - current_checks

            if added_checks or removed_checks:
                pytest.fail(
                    f"{schema_name}.{field_name}: Validation checks changed\n"
                    f"  Added:   {sorted(added_checks) if added_checks else 'none'}\n"
                    f"  Removed: {sorted(removed_checks) if removed_checks else 'none'}\n"
                    "If intentional, run: UPDATE_SNAPSHOTS=1 pytest ..."
                )

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_primary_key_field_exists(self, schema_name: str) -> None:
        """Each Silver schema MUST have entity_id as the base primary key.

        All schemas inherit from ETLRecordSchema which defines entity_id as
        the primary business key. This test verifies:
        1. entity_id field exists
        2. entity_id is non-nullable (required=True, nullable=False)

        NOTE: Other fields ending in _id or _chembl_id are typically foreign keys
        or alternate identifiers, not primary keys. The actual PK is entity_id.
        """
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        # Check entity_id exists (base PK from ETLRecordSchema)
        assert "entity_id" in fields, (
            f"{schema_name}: Missing entity_id field.\n"
            "All schemas MUST inherit from ETLRecordSchema which defines entity_id."
        )

        # entity_id MUST NOT be nullable
        if fields["entity_id"]["nullable"]:
            pytest.fail(
                f"{schema_name}.entity_id: Primary key MUST NOT be nullable.\n"
                "ETLRecordSchema defines entity_id with nullable=False."
            )

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_etl_metadata_fields_present(self, schema_name: str) -> None:
        """Silver schemas MUST have ETL metadata fields from ETLRecordSchema.

        Required metadata fields:
        - _ingestion_ts: When record was ingested (ISO 8601 timestamp)
        - _run_id: Pipeline run identifier
        - _run_type: Type of pipeline run (incremental/backfill/rebuild)
        - _dq_warn: Data quality warning flag
        - _dq_error: Data quality error flag
        - _index: Sequential record index
        - content_hash: SHA256 hash for deduplication
        - entity_id: Unique business identifier
        """
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        required_metadata = {
            "_ingestion_ts": "Record ingestion timestamp",
            "_run_id": "Pipeline run identifier for traceability",
            "_run_type": "Type of pipeline run",
            "_dq_warn": "Data quality warning flag",
            "_dq_error": "Data quality error flag",
            "_index": "Sequential record index",
            "content_hash": "SHA256 hash for deduplication (SCD Type 2)",
            "entity_id": "Unique business identifier",
        }

        for meta_field, description in required_metadata.items():
            assert meta_field in fields, (
                f"{schema_name}: Missing required metadata field '{meta_field}'\n"
                f"Purpose: {description}\n"
                "All Silver schemas MUST inherit from ETLRecordSchema."
            )

            # Metadata fields MUST NOT be nullable
            if fields[meta_field]["nullable"]:
                pytest.fail(
                    f"{schema_name}.{meta_field}: Metadata field MUST NOT be nullable"
                )


@pytest.mark.contracts
@pytest.mark.no_api
class TestSchemaDocumentation:
    """Tests ensuring Silver schemas have proper documentation."""

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_schema_has_docstring(self, schema_name: str) -> None:
        """Each Silver schema MUST have a docstring."""
        schema_class = SILVER_SCHEMAS[schema_name]

        assert schema_class.__doc__, (
            f"{schema_name}: Schema class MUST have a docstring.\n"
            "Example:\n"
            '  """Pandera schema for ChEMBL Activity entity."""'
        )

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_fields_have_descriptions(self, schema_name: str) -> None:
        """All Silver schema fields SHOULD have descriptions.

        Descriptions are critical for:
        - Data catalog documentation
        - Downstream consumer understanding
        - Gold contract generation
        """
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        fields_without_description = [
            field for field, meta in fields.items() if not meta.get("description")
        ]

        if fields_without_description:
            pytest.fail(
                f"{schema_name}: {len(fields_without_description)} fields missing descriptions:\n"
                + "\n".join(f"  - {f}" for f in sorted(fields_without_description))
                + "\n\nAdd descriptions via pa.Field(description='...')"
            )
