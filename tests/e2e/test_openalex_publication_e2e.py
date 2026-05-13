"""E2E tests for OpenAlex Publication pipeline.

Tests the complete pipeline execution from fetch to Silver layer.
Uses VCR cassettes for HTTP requests and local file storage.

Cassettes location: tests/fixtures/vcr/openalex/

Note:
    OpenAlex is a DOI-based enrichment provider. The pipeline fetches
    metadata for known DOIs and transforms it into the unified Silver schema.

Recording cassettes:
    pytest tests/e2e/test_openalex_publication_e2e.py --vcr-record=new_episodes -v
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

pytestmark = pytest.mark.usefixtures("relaxed_dq_env")

# Stable DOIs for deterministic cassette playback.
OPENALEX_TEST_DOIS = (
    "10.1038/s41586-020-2649-2",  # Nature 2020
    "10.1126/science.abc4765",  # Science 2020
    "10.1016/j.cell.2020.06.043",  # Cell 2020
)


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_openalex_publication_full_cycle(e2e_data_dir: Path) -> None:
    """E2E: OpenAlex Publication pipeline from fetch to Silver.

    Verifies:
    1. Publication data is fetched via DOI resolution
    2. Bronze files are created
    3. Silver table contains expected records
    """
    ctx = create_test_context(
        "openalex_publication",
        limit=10,
        filter_ids=OPENALEX_TEST_DOIS,
        filter_field="doi",
    )

    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    bronze_files = assert_bronze_files_exist(e2e_data_dir, "openalex", "publication")
    assert len(bronze_files) >= 1

    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "openalex_publication", expected_min=1
    )
    assert silver_count <= 10

    records = get_silver_records(e2e_data_dir, "openalex_publication")
    for record in records:
        doi = record.get("publication_doi") or record.get("doi")
        assert doi is not None, "OpenAlex records must have a DOI"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_openalex_publication_metadata_fields(e2e_data_dir: Path) -> None:
    """E2E: Verify OpenAlex-specific metadata fields are extracted.

    OpenAlex provides rich metadata: title, authors, cited_by_count, etc.
    """
    ctx = create_test_context(
        "openalex_publication",
        limit=10,
        filter_ids=OPENALEX_TEST_DOIS,
        filter_field="doi",
    )

    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    records = get_silver_records(e2e_data_dir, "openalex_publication")
    assert len(records) >= 1, "Should have at least one OpenAlex record"

    metadata_fields = ["title", "publication_year"]
    records_with_metadata = sum(
        1 for r in records if any(r.get(f) is not None for f in metadata_fields)
    )
    assert records_with_metadata >= 1, "At least one record should have metadata"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_openalex_publication_citation_fields(e2e_data_dir: Path) -> None:
    """E2E: Verify citation count fields are extracted from OpenAlex."""
    ctx = create_test_context(
        "openalex_publication",
        limit=10,
        filter_ids=OPENALEX_TEST_DOIS,
        filter_field="doi",
    )

    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    records = get_silver_records(e2e_data_dir, "openalex_publication")
    for record in records:
        citations = record.get("citations_received")
        if citations is not None:
            assert isinstance(citations, int), (
                f"citations_received should be int, got {type(citations)}"
            )
            assert citations >= 0, "Citation count must be non-negative"
