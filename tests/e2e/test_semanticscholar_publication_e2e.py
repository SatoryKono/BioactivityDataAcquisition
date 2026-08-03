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
"""E2E tests for Semantic Scholar Publication pipeline.

Tests the complete pipeline execution from fetch to Silver layer.
Uses VCR cassettes for HTTP requests and local file storage.

Cassettes location: tests/fixtures/vcr/semanticscholar/

Note:
    Semantic Scholar is a DOI-based enrichment provider. The pipeline fetches
    metadata for known DOIs and transforms it into the unified Silver schema.

Recording cassettes:
    pytest tests/e2e/test_semanticscholar_publication_e2e.py --vcr-record=new_episodes -v
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.helpers.vcr_config import build_base_vcr_config

from .conftest import (
    assert_bronze_files_exist,
    assert_silver_table_has_records,
    create_test_context,
    get_silver_records,
    run_pipeline_or_skip_transient,
)

pytestmark = pytest.mark.usefixtures("relaxed_dq_env")


@pytest.fixture
def vcr_config(vcr_cassette_dir) -> dict[str, Any]:
    """Configure VCR for Semantic Scholar E2E tests."""
    return build_base_vcr_config(
        cassette_library_dir=vcr_cassette_dir,
        decode_compressed_response=True,
    )


# Stable DOIs for deterministic cassette playback.
S2_TEST_DOIS = (
    "10.1038/s41586-020-2649-2",  # Nature 2020
    "10.1126/science.abc4765",  # Science 2020
    "10.1016/j.cell.2020.06.043",  # Cell 2020
)


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_semanticscholar_publication_full_cycle(
    e2e_data_dir: Path,
) -> None:
    """E2E: Semantic Scholar Publication pipeline from fetch to Silver.

    Verifies:
    1. Publication data is fetched via DOI resolution
    2. Bronze files are created
    3. Silver table contains expected records
    """
    ctx = create_test_context(
        "semanticscholar_publication",
        limit=10,
        filter_ids=S2_TEST_DOIS,
        filter_field="doi",
    )

    await run_pipeline_or_skip_transient(ctx)

    bronze_files = assert_bronze_files_exist(
        e2e_data_dir, "semanticscholar", "publication"
    )
    assert len(bronze_files) >= 1

    silver_count = await assert_silver_table_has_records(
        e2e_data_dir,
        "semanticscholar_publication",
        expected_min=1,
    )
    assert silver_count <= 10

    records = await get_silver_records(e2e_data_dir, "semanticscholar_publication")
    for record in records:
        doi = record.get("publication_doi") or record.get("doi")
        assert doi is not None, "Semantic Scholar records must have a DOI"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_semanticscholar_publication_metadata_fields(
    e2e_data_dir: Path,
) -> None:
    """E2E: Verify Semantic Scholar metadata fields are extracted.

    Semantic Scholar provides title, authors, year, citation counts, etc.
    """
    ctx = create_test_context(
        "semanticscholar_publication",
        limit=10,
        filter_ids=S2_TEST_DOIS,
        filter_field="doi",
    )

    await run_pipeline_or_skip_transient(ctx)

    records = await get_silver_records(e2e_data_dir, "semanticscholar_publication")
    assert len(records) >= 1, "Should have at least one S2 record"

    metadata_fields = ["title", "publication_year"]
    records_with_metadata = sum(
        1 for r in records if any(r.get(f) is not None for f in metadata_fields)
    )
    assert records_with_metadata >= 1, "At least one record should have metadata"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_semanticscholar_publication_citation_fields(
    e2e_data_dir: Path,
) -> None:
    """E2E: Verify citation fields from Semantic Scholar."""
    ctx = create_test_context(
        "semanticscholar_publication",
        limit=10,
        filter_ids=S2_TEST_DOIS,
        filter_field="doi",
    )

    await run_pipeline_or_skip_transient(ctx)

    records = await get_silver_records(e2e_data_dir, "semanticscholar_publication")
    for record in records:
        citations = record.get("citations_received")
        if citations is not None:
            assert isinstance(citations, int), (
                f"citations_received should be int, got {type(citations)}"
            )
            assert citations >= 0, "Citation count must be non-negative"
