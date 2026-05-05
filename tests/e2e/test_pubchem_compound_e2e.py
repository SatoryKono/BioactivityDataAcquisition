"""E2E tests for PubChem Compound pipeline.

Tests the complete pipeline execution from fetch to Gold layer.
Uses VCR cassettes for HTTP requests and local file storage.

Cassettes location: tests/fixtures/vcr/pubchem/
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.helpers.vcr_config import build_base_vcr_config

from bioetl.composition.bootstrap import bootstrap_pipeline_runner

from .conftest import (
    assert_bronze_files_exist,
    assert_bronze_metadata_files_exist,
    assert_run_ledger_has_events,
    assert_run_manifest_exists,
    assert_silver_table_has_records,
    create_test_context,
    get_silver_records,
)


@pytest.fixture(scope="module")
def vcr_config(vcr_cassette_dir) -> dict[str, Any]:
    """Configure VCR for PubChem Compound E2E tests."""
    return build_base_vcr_config(
        cassette_library_dir=vcr_cassette_dir,
        decode_compressed_response=True,
    )


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pubchem_compound_full_cycle(e2e_data_dir: Path):
    """E2E: PubChem Compound pipeline from fetch to Silver.

    Note: PubChem requires a query parameter for compound search.
    """
    # Arrange - PubChem requires query
    ctx = create_test_context("pubchem_compound", limit=5, query="aspirin")

    # Act
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Control-plane artifacts
    manifest_payload = assert_run_manifest_exists(e2e_data_dir, ctx.run_id)
    assert manifest_payload["pipeline_name"] == "pubchem_compound"
    ledger_entries = assert_run_ledger_has_events(
        e2e_data_dir,
        ctx.run_id,
        expected_events=("manifest_created", "run_started", "run_finished"),
    )
    assert all(
        entry.get("manifest_id") == manifest_payload["manifest_id"]
        for entry in ledger_entries
    )

    # Assert - Bronze layer
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "pubchem", "compound")
    assert len(bronze_files) >= 1
    bronze_metadata_files = assert_bronze_metadata_files_exist(
        e2e_data_dir,
        "pubchem",
        "compound",
    )
    assert len(bronze_metadata_files) >= 1

    # Assert - Silver layer
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "pubchem_compound", expected_min=1
    )
    assert silver_count <= 5

    # Assert - Schema validation
    records = get_silver_records(e2e_data_dir, "pubchem_compound")
    required_fields = ["molecule_id"]
    for record in records:
        for field in required_fields:
            assert field in record, f"Missing required field: {field}"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pubchem_compound_structural_fields(e2e_data_dir: Path):
    """E2E: Verify structural fields are extracted for PubChem compounds.

    Compounds should have molecular formula, weight, and SMILES.
    """
    # Arrange
    ctx = create_test_context("pubchem_compound", limit=5, query="caffeine")

    # Act
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Check structural fields
    records = get_silver_records(e2e_data_dir, "pubchem_compound")

    for record in records:
        # CID must always be present
        assert record.get("molecule_id") is not None

        # Check structural data extraction - most compounds should have basic fields
        has_formula = record.get("molecular_formula") is not None
        has_weight = record.get("molecular_weight") is not None
        has_smiles = (
            record.get("canonical_smiles") is not None
            or record.get("isomeric_smiles") is not None
        )

        assert has_formula or has_weight or has_smiles, (
            f"Compound {record.get('molecule_id')} missing all structural fields"
        )


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pubchem_compound_query_filter(e2e_data_dir: Path):
    """E2E: Verify query parameter filters compounds correctly.

    Searching for 'ibuprofen' should return ibuprofen-related compounds.
    """
    # Arrange
    ctx = create_test_context("pubchem_compound", limit=3, query="ibuprofen")

    # Act
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Silver layer should have records
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "pubchem_compound", expected_min=1
    )
    assert silver_count >= 1

    # Get records - should be related to ibuprofen
    records = get_silver_records(e2e_data_dir, "pubchem_compound")

    assert len(records) >= 1

    ibuprofen_matches = [
        record
        for record in records
        if record.get("molecule_id") == "3672"
        or "ibuprofen" in str(record.get("iupac_name") or "").lower()
    ]
    assert ibuprofen_matches, (
        "PubChem query-filter replay must include the ibuprofen record identity "
        "(CID 3672 or ibuprofen-correlated IUPAC name)"
    )

    ibuprofen_record = ibuprofen_matches[0]
    assert ibuprofen_record.get("molecular_formula") == "C13H18O2"
