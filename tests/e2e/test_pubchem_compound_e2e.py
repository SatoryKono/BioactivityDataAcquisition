"""E2E tests for PubChem Compound pipeline.

Tests the complete pipeline execution from fetch to Gold layer.
Uses VCR cassettes for HTTP requests and local file storage.
"""

from pathlib import Path

import pytest

from bioetl.composition.bootstrap import bootstrap_pipeline

from .conftest import (
    assert_bronze_files_exist,
    assert_silver_table_has_records,
    create_test_context,
    get_silver_records,
)


@pytest.fixture(scope="module")
def vcr_cassette_dir() -> Path:
    """Path to VCR cassettes directory."""
    return Path(__file__).parent.parent / "fixtures" / "vcr"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
@pytest.mark.skip(reason="pubchempy canonical_smiles deprecation warning - needs client update")
async def test_pubchem_compound_full_cycle(e2e_data_dir: Path):
    """E2E: PubChem Compound pipeline from fetch to Silver.

    Note: PubChem requires a query parameter for compound search.

    SKIPPED: pubchempy library raises PubChemPyDeprecationWarning
    for canonical_smiles. Client needs update to use connectivity_smiles.
    """
    # Arrange - PubChem requires query
    ctx = create_test_context("pubchem_compound", limit=5, query="aspirin")

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Bronze layer
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "pubchem", "compound")
    assert len(bronze_files) >= 1

    # Assert - Silver layer
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "pubchem_compound", expected_min=1
    )
    assert silver_count <= 5

    # Assert - Schema validation
    records = get_silver_records(e2e_data_dir, "pubchem_compound")
    required_fields = ["cid"]
    for record in records:
        for field in required_fields:
            assert field in record, f"Missing required field: {field}"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
@pytest.mark.skip(reason="pubchempy canonical_smiles deprecation warning - needs client update")
async def test_pubchem_compound_structural_fields(e2e_data_dir: Path):
    """E2E: Verify structural fields are extracted for PubChem compounds.

    Compounds should have molecular formula, weight, and SMILES.
    """
    # Arrange
    ctx = create_test_context("pubchem_compound", limit=5, query="caffeine")

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Check structural fields
    records = get_silver_records(e2e_data_dir, "pubchem_compound")

    for record in records:
        # CID must always be present
        assert record.get("cid") is not None

        # Check structural data extraction - most compounds should have basic fields
        has_formula = record.get("molecular_formula") is not None
        has_weight = record.get("molecular_weight") is not None
        has_smiles = (
            record.get("canonical_smiles") is not None
            or record.get("isomeric_smiles") is not None
        )

        assert has_formula or has_weight or has_smiles, (
            f"Compound {record.get('cid')} missing all structural fields"
        )


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
@pytest.mark.skip(reason="pubchempy canonical_smiles deprecation warning - needs client update")
async def test_pubchem_compound_query_filter(e2e_data_dir: Path):
    """E2E: Verify query parameter filters compounds correctly.

    Searching for 'ibuprofen' should return ibuprofen-related compounds.
    """
    # Arrange
    ctx = create_test_context("pubchem_compound", limit=3, query="ibuprofen")

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Silver layer should have records
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "pubchem_compound", expected_min=1
    )
    assert silver_count >= 1

    # Get records - should be related to ibuprofen
    records = get_silver_records(e2e_data_dir, "pubchem_compound")

    # At least one record should exist
    assert len(records) >= 1
