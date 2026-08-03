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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
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

import os
from pathlib import Path

import pytest

from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
from tests.contract.silver_schemas.conftest import (
    SILVER_SCHEMAS,
    assert_schema_matches_snapshot,
    extract_field_metadata,
)

UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"


@pytest.mark.contracts
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
        assert_schema_matches_snapshot(
            schema_name,
            snapshots_dir=snapshots_dir,
            update_snapshots=UPDATE_SNAPSHOTS,
        )

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_primary_key_field_exists(self, schema_name: str) -> None:
        """Silver schema MUST expose both technical and business PK fields."""
        schema_class = SILVER_SCHEMAS[schema_name]
        fields = extract_field_metadata(schema_class)

        yaml_config = load_pipeline_config(schema_name)

        # Some configs may rely on composition defaults (runner_builder)
        # where technical_primary_key implicitly defaults to "entity_id".
        # Tests should remain robust to such defaults while still verifying
        # that the referenced fields exist and are non-nullable in Silver.
        technical_pk = yaml_config.technical_primary_key
        business_pks = list(yaml_config.business_primary_keys)

        assert technical_pk in fields, (
            f"{schema_name}: Missing technical_primary_key '{technical_pk}' in Silver schema"
        )
        assert not fields[technical_pk]["nullable"], (
            f"{schema_name}.{technical_pk}: technical_primary_key MUST NOT be nullable"
        )

        missing_business = [pk for pk in business_pks if pk not in fields]
        assert not missing_business, (
            f"{schema_name}: Missing business_primary_keys in Silver schema: {missing_business}"
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
