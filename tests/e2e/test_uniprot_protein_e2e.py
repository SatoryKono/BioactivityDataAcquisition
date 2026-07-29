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
    assert_gold_table_has_records,
    assert_silver_table_has_records,
    create_test_context,
    get_silver_records,
)
from tests.helpers.e2e_schema_assertions import assert_records_have_required_fields

pytestmark = pytest.mark.usefixtures("relaxed_dq_env")


@pytest.fixture
def vcr_cassette_name(request: pytest.FixtureRequest) -> str:
    """Reuse one equivalent protein cassette for duplicate E2E payloads."""
    if request.node.name == "test_uniprot_protein_sequence_fields":
        return "test_uniprot_protein_metadata_fields"
    return request.node.name


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_uniprot_protein_full_cycle(e2e_data_dir: Path):
    """E2E: UniProt Protein pipeline from fetch through Gold.

    Verifies:
    1. Protein data is fetched from UniProt
    2. Silver table contains expected records
    3. Gold SCD2 table is materialized
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
    silver_count = await assert_silver_table_has_records(
        e2e_data_dir, "uniprot_protein", expected_min=1
    )
    assert silver_count <= 5

    # Assert - Gold layer (sink.gold.mode=scd2)
    gold_count = await assert_gold_table_has_records(
        e2e_data_dir, "uniprot_protein", expected_min=1
    )
    assert gold_count >= 1

    # Assert - Schema validation
    records = await get_silver_records(e2e_data_dir, "uniprot_protein")
    assert_records_have_required_fields(
        records,
        ("accession",),
        entity_label="uniprot_protein.silver",
    )


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
    records = await get_silver_records(e2e_data_dir, "uniprot_protein")

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
    records = await get_silver_records(e2e_data_dir, "uniprot_protein")

    for record in records:
        # Accession must always be present
        assert record.get("accession") is not None

        # Check sequence_length if present
        seq_length = record.get("sequence_length")
        if seq_length is not None:
            assert seq_length >= 0, (
                f"Invalid sequence_length {seq_length} for {record.get('accession')}"
            )
