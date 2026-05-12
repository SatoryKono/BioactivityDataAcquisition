"""E2E tests for UniProt Protein pipeline.

Tests the complete pipeline execution from fetch to Gold layer.
Uses VCR cassettes for HTTP requests and local file storage.

Cassettes location: tests/fixtures/vcr/uniprot/
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner

from .conftest import (
    assert_bronze_files_exist,
    assert_silver_table_has_records,
    create_test_context,
    get_silver_records,
)


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
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Bronze layer
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "uniprot", "protein")
    assert len(bronze_files) >= 1

    # Assert - Silver layer
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "uniprot_protein", expected_min=1
    )
    assert silver_count <= 5

    # Assert - Schema validation
    records = get_silver_records(e2e_data_dir, "uniprot_protein")
    required_fields = ["accession"]
    for record in records:
        for field in required_fields:
            assert field in record, f"Missing required field: {field}"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_uniprot_protein_metadata_fields(e2e_data_dir: Path):
    """E2E: Verify protein metadata fields are extracted.

    Proteins should have entry_name, protein_name, and organism information.
    """
    # Arrange
    ctx = create_test_context("uniprot_protein", limit=5)

    # Act
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Check metadata fields
    records = get_silver_records(e2e_data_dir, "uniprot_protein")

    for record in records:
        # Accession must always be present
        assert record.get("accession") is not None

        # Check metadata extraction
        has_entry_name = record.get("entry_name") is not None
        has_protein_name = record.get("protein_name") is not None

        # Most proteins should have basic metadata
        assert has_entry_name or has_protein_name, (
            f"Protein {record.get('accession')} missing basic metadata"
        )


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_uniprot_protein_sequence_fields(e2e_data_dir: Path):
    """E2E: Verify sequence-related fields are extracted.

    Proteins should have sequence_length and potentially full sequence.
    """
    # Arrange
    ctx = create_test_context("uniprot_protein", limit=5)

    # Act
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Check sequence fields
    records = get_silver_records(e2e_data_dir, "uniprot_protein")

    for record in records:
        # Accession must always be present
        assert record.get("accession") is not None

        # Check sequence_length if present
        seq_length = record.get("sequence_length")
        if seq_length is not None:
            assert seq_length >= 0, (
                f"Invalid sequence_length {seq_length} for {record.get('accession')}"
            )
