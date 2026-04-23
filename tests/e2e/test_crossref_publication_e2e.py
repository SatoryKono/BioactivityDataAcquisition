"""E2E tests for CrossRef Publication pipeline.

Tests the complete pipeline execution from fetch to Silver layer.
Uses VCR cassettes for HTTP requests and local file storage.

Cassettes location: tests/fixtures/vcr/crossref/

Note:
    CrossRef is a DOI-based enrichment provider. The pipeline fetches
    metadata for known DOIs and transforms it into the unified Silver schema.

Recording cassettes:
    pytest tests/e2e/test_crossref_publication_e2e.py --vcr-record=new_episodes -v
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

# VCR cassette directory for CrossRef E2E tests
CASSETTE_DIR = Path(__file__).parent.parent / "fixtures" / "vcr" / "crossref"

# Stable DOIs for deterministic cassette playback.
# Selected from well-known, long-lived publications unlikely to change.
CROSSREF_TEST_DOIS = (
    "10.1038/s41586-020-2649-2",  # Nature 2020
    "10.1126/science.abc4765",  # Science 2020
    "10.1016/j.cell.2020.06.043",  # Cell 2020
)


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    """Configure VCR for CrossRef Publication E2E tests."""
    return {
        "cassette_library_dir": str(CASSETTE_DIR),
        "record_mode": os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "decode_compressed_response": True,
    }


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_crossref_publication_full_cycle(e2e_data_dir: Path) -> None:
    """E2E: CrossRef Publication pipeline from fetch to Silver.

    Verifies:
    1. Publication data is fetched via DOI resolution
    2. Bronze files are created
    3. Silver table contains expected records with DOI field
    """
    ctx = create_test_context(
        "crossref_publication",
        limit=10,
        filter_ids=CROSSREF_TEST_DOIS,
        filter_field="doi",
    )

    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    bronze_files = assert_bronze_files_exist(e2e_data_dir, "crossref", "publication")
    assert len(bronze_files) >= 1

    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "crossref_publication", expected_min=1
    )
    assert silver_count <= 10

    records = get_silver_records(e2e_data_dir, "crossref_publication")
    for record in records:
        doi = record.get("publication_doi") or record.get("doi")
        assert doi is not None, "CrossRef records must have a DOI"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_crossref_publication_metadata_fields(e2e_data_dir: Path) -> None:
    """E2E: Verify CrossRef-specific metadata fields are extracted.

    CrossRef publications should contain title, authors, journal, year.
    """
    ctx = create_test_context(
        "crossref_publication",
        limit=10,
        filter_ids=CROSSREF_TEST_DOIS,
        filter_field="doi",
    )

    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    records = get_silver_records(e2e_data_dir, "crossref_publication")
    assert len(records) >= 1, "Should have at least one CrossRef record"

    metadata_fields = ["title", "publication_year", "publisher"]
    records_with_metadata = sum(
        1 for r in records if any(r.get(f) is not None for f in metadata_fields)
    )
    assert records_with_metadata >= 1, "At least one record should have metadata"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_crossref_publication_citation_fields(e2e_data_dir: Path) -> None:
    """E2E: Verify citation count fields are extracted."""
    ctx = create_test_context(
        "crossref_publication",
        limit=10,
        filter_ids=CROSSREF_TEST_DOIS,
        filter_field="doi",
    )

    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    records = get_silver_records(e2e_data_dir, "crossref_publication")
    for record in records:
        citations = record.get("citations_received")
        if citations is not None:
            assert isinstance(citations, int), (
                f"citations_received should be int, got {type(citations)}"
            )
            assert citations >= 0, "Citation count must be non-negative"
