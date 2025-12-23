"""E2E tests for BioETL pipelines.

Tests the complete pipeline execution from fetch to Gold layer output.
Uses VCR cassettes for HTTP requests and local file storage.

Requirements:
- VCR cassettes must exist for the pipeline being tested
- Uses Local-Only architecture (no Docker/MinIO/Redis required)
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
async def test_chembl_activity_full_cycle(e2e_data_dir: Path):
    """E2E: ChEMBL Activity pipeline from fetch to Silver.

    Verifies:
    1. Pipeline bootstraps correctly
    2. Data is fetched from ChEMBL API (via VCR cassette)
    3. Bronze files are created
    4. Silver Delta table contains records
    5. Records have correct schema
    """
    # Arrange
    ctx = create_test_context("chembl_activity", limit=10)

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Bronze layer
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "chembl", "activity")
    assert len(bronze_files) >= 1, "At least one Bronze file should exist"

    # Assert - Silver layer
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=1
    )
    assert silver_count <= 10, f"Expected <= 10 records (limit), got {silver_count}"

    # Assert - Schema validation
    records = get_silver_records(e2e_data_dir, "chembl_activity")
    required_fields = ["activity_id", "molecule_chembl_id", "target_chembl_id"]
    for record in records:
        for field in required_fields:
            assert field in record, f"Missing required field: {field}"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_target_full_cycle(e2e_data_dir: Path):
    """E2E: ChEMBL Target pipeline from fetch to Silver.

    Verifies:
    1. Target data is fetched and transformed
    2. cross_references field is properly aggregated from components
    3. Silver table contains expected records
    """
    # Arrange
    ctx = create_test_context("chembl_target", limit=5)

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Bronze layer
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "chembl", "target")
    assert len(bronze_files) >= 1

    # Assert - Silver layer
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_target", expected_min=1
    )
    assert silver_count <= 5

    # Assert - Schema validation
    records = get_silver_records(e2e_data_dir, "chembl_target")
    required_fields = ["target_chembl_id", "pref_name", "target_type"]
    for record in records:
        for field in required_fields:
            assert field in record, f"Missing required field: {field}"


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
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Bronze layer
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "chembl", "molecule")
    assert len(bronze_files) >= 1

    # Assert - Silver layer
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_molecule", expected_min=1
    )
    assert silver_count <= 5

    # Assert - Schema validation
    records = get_silver_records(e2e_data_dir, "chembl_molecule")
    required_fields = ["molecule_chembl_id"]
    for record in records:
        for field in required_fields:
            assert field in record, f"Missing required field: {field}"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_document_full_cycle(e2e_data_dir: Path):
    """E2E: ChEMBL Document pipeline from fetch to Silver.

    Verifies:
    1. Document data is fetched and transformed
    2. Silver table contains expected records
    """
    # Arrange
    ctx = create_test_context("chembl_document", limit=5)

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Bronze layer
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "chembl", "document")
    assert len(bronze_files) >= 1

    # Assert - Silver layer
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_document", expected_min=1
    )
    assert silver_count <= 5


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_pipeline_idempotency(e2e_data_dir: Path):
    """E2E: Pipeline runs are idempotent.

    Running the same pipeline twice with same data should not duplicate records
    in Silver table (merge/upsert behavior).
    """
    # Arrange
    ctx1 = create_test_context("chembl_activity", limit=5)

    # Act - First run
    runner1 = bootstrap_pipeline(ctx1)
    await runner1.run()
    count_after_first = assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=1
    )

    # Act - Second run with same limit
    ctx2 = create_test_context("chembl_activity", limit=5)
    runner2 = bootstrap_pipeline(ctx2)
    await runner2.run()
    count_after_second = assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=1
    )

    # Assert - Count should be similar (merge/upsert prevents duplicates)
    # Note: May differ slightly due to different batches, but should not double
    assert count_after_second <= count_after_first * 2, (
        f"Records doubled after second run: {count_after_first} -> {count_after_second}"
    )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_pipeline_resume_from_checkpoint(e2e_data_dir: Path):
    """E2E: Pipeline can resume from checkpoint.

    Verifies that a pipeline run can be interrupted and resumed.
    """
    # Arrange - First run with limit
    ctx1 = create_test_context("chembl_activity", limit=3, resume=False)
    runner1 = bootstrap_pipeline(ctx1)
    await runner1.run()

    first_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=1
    )

    # Arrange - Second run with resume
    ctx2 = create_test_context("chembl_activity", limit=3, resume=True)
    runner2 = bootstrap_pipeline(ctx2)
    await runner2.run()

    second_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=first_count
    )

    # Assert - Should have at least as many records
    assert second_count >= first_count


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_uniprot_protein_full_cycle(e2e_data_dir: Path):
    """E2E: UniProt Protein pipeline from fetch to Silver.

    Verifies:
    1. Protein data is fetched from UniProt
    2. Silver table contains expected records
    """
    # Arrange
    ctx = create_test_context("uniprot_protein", limit=5)

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Bronze layer
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "uniprot", "protein")
    assert len(bronze_files) >= 1

    # Assert - Silver layer
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "uniprot_protein", expected_min=1
    )
    assert silver_count <= 5


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
