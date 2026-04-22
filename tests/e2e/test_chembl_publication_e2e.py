"""E2E tests for ChEMBL Publication pipeline.

Tests the complete pipeline execution from fetch to Gold layer.
Uses VCR cassettes for HTTP requests and local file storage.

Cassettes location: tests/fixtures/vcr/chembl/

.. versionchanged:: 2.0.0
    Renamed from test_chembl_document_e2e to test_chembl_publication_e2e (ADR-024).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from bioetl.composition.bootstrap import bootstrap_pipeline_runner
from .conftest import (
    assert_bronze_files_exist,
    assert_silver_table_has_records,
    create_test_context,
    get_silver_records,
)

# VCR cassette directory for ChEMBL E2E tests
CASSETTE_DIR = Path(__file__).parent.parent / "fixtures" / "vcr" / "chembl"

# Stable subset of IDs available in recorded cassette.
PUBLICATION_TEST_IDS = (
    "CHEMBL1121421",
    "CHEMBL1121493",
    "CHEMBL1121680",
    "CHEMBL1121695",
    "CHEMBL1121721",
    "CHEMBL1121751",
    "CHEMBL1121774",
    "CHEMBL1121806",
    "CHEMBL1121940",
    "CHEMBL1121981",
)


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    """Configure VCR for ChEMBL Publication E2E tests."""
    return {
        "cassette_library_dir": str(CASSETTE_DIR),
        "record_mode": os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "decode_compressed_response": True,
    }


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_publication_full_cycle(e2e_data_dir: Path):
    """E2E: ChEMBL Publication pipeline from fetch to Silver.

    Verifies:
    1. Publication data is fetched and transformed
    2. Silver table contains expected records
    """
    # Arrange - use cassette-backed IDs for deterministic playback
    ctx = create_test_context(
        "chembl_publication",
        limit=100,
        filter_ids=PUBLICATION_TEST_IDS,
        filter_field="publication_id",
    )

    # Act
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Bronze layer
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "chembl", "publication")
    assert len(bronze_files) >= 1

    # Assert - Silver layer
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_publication", expected_min=1
    )
    assert silver_count <= 100

    # Assert - Schema validation
    records = get_silver_records(e2e_data_dir, "chembl_publication")
    required_fields = ["publication_id", "publication_type", "title"]
    for record in records:
        for field in required_fields:
            assert field in record, f"Missing required field: {field}"
            assert record.get(field) not in (None, ""), (
                f"Required field must be populated: {field}"
            )


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_publication_metadata_fields(e2e_data_dir: Path):
    """E2E: Verify publication-related fields are extracted.

    Publications may contain journal, year, DOI and other metadata.
    """
    # Arrange - use cassette-backed IDs for deterministic playback
    ctx = create_test_context(
        "chembl_publication",
        limit=100,
        filter_ids=PUBLICATION_TEST_IDS,
        filter_field="publication_id",
    )

    # Act
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Check publication fields
    records = get_silver_records(e2e_data_dir, "chembl_publication")

    # Publication pipeline records should always have core metadata populated.
    for record in records:
        assert record.get("title") not in (None, "")
        assert record.get("publication_year") is not None
        assert record.get("publication_type") == "PUBLICATION"
        assert record.get("publication_type_unified") == "Journal Article"

        prefixed_doi = record.get("publication_doi")
        raw_doi = record.get("doi")
        if prefixed_doi is not None and raw_doi is not None:
            assert prefixed_doi == raw_doi

        prefixed_pmid = record.get("publication_pmid")
        raw_pmid = record.get("pmid")
        if prefixed_pmid is not None and raw_pmid is not None:
            assert prefixed_pmid == raw_pmid

    assert any(
        (record.get("publication_doi") or record.get("doi"))
        or (record.get("publication_pmid") or record.get("pmid"))
        for record in records
    ), "Expected at least one external publication identifier in cassette-backed data"
