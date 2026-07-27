"""E2E tests for ChEMBL Molecule pipeline.

Tests the complete pipeline execution from fetch to Gold layer.
Uses VCR cassettes for HTTP requests and local file storage.

Cassettes location: tests/fixtures/vcr/chembl/
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .conftest import (
    assert_bronze_files_exist,
    assert_silver_table_has_records,
    create_test_context,
    get_silver_records,
    run_pipeline_or_skip_transient,
)
from tests.helpers.e2e_schema_assertions import assert_records_have_required_fields

pytestmark = pytest.mark.usefixtures("relaxed_dq_env")


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_molecule_full_cycle(e2e_data_dir: Path):
    """E2E: ChEMBL Molecule pipeline from fetch to Silver.

    Verifies:
    1. Molecule data is fetched and transformed
    2. Silver table contains expected records
    3. Structural data fields are present
    """
    # Arrange
    ctx = create_test_context("chembl_molecule", limit=5)

    # Act
    await run_pipeline_or_skip_transient(ctx)

    # Assert - Bronze layer
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "chembl", "molecule")
    assert len(bronze_files) >= 1

    # Assert - Silver layer
    silver_count = await assert_silver_table_has_records(
        e2e_data_dir, "chembl_molecule", expected_min=1
    )
    assert silver_count <= 5

    # Assert - Schema validation
    records = await get_silver_records(e2e_data_dir, "chembl_molecule")
    assert_records_have_required_fields(
        records,
        ("molecule_id",),
        entity_label="chembl_molecule.silver",
    )


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_molecule_structural_fields(e2e_data_dir: Path):
    """E2E: Verify structural identity fields for molecules (schema-backed)."""
    ctx = create_test_context("chembl_molecule", limit=5)
    await run_pipeline_or_skip_transient(ctx)
    records = await get_silver_records(e2e_data_dir, "chembl_molecule")
    assert_records_have_required_fields(
        records,
        ("molecule_id",),
        entity_label="chembl_molecule.structural",
    )
