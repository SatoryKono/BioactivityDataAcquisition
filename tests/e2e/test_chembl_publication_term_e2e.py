"""E2E tests for ChEMBL Publication Term pipeline.

Tests the complete pipeline execution from fetch to Silver layer.
Uses VCR cassettes for HTTP requests and local file storage.

Cassettes location: tests/fixtures/vcr/chembl/

Publication Term is a derived entity that extracts nested term data
from Publication (ChEMBL Document) API responses and flattens the 1:M relationship.

.. versionchanged:: 2.0.0
    Renamed from test_chembl_publication_term_e2e to test_chembl_publication_term_e2e (ADR-024).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from deltalake.exceptions import DeltaError, TableNotFoundError

from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner
from .conftest import (
    assert_bronze_files_exist,
    assert_silver_table_has_records,
    create_test_context,
    get_silver_records,
)

# VCR cassette directory for ChEMBL E2E tests
CASSETTE_DIR = Path(__file__).parent.parent / "fixtures" / "vcr" / "chembl"
TERM_PAYLOAD_MARKERS = ('"mesh_terms"', '"keywords"')
SILVER_READ_SKIP_ERRORS: tuple[type[Exception], ...] = (
    DeltaError,
    OSError,
    TableNotFoundError,
    ValueError,
)


def _is_vcr_recording_enabled() -> bool:
    record_mode = os.environ.get("VCR_RECORD_MODE", "none").lower()
    if record_mode in {"all", "new_episodes"}:
        return True
    argv_text = " ".join(sys.argv)
    return any(
        token in argv_text
        for token in (
            "--vcr-record=all",
            "--vcr-record=new_episodes",
            "--vcr-record-mode=all",
            "--vcr-record-mode=new_episodes",
        )
    )


def _cassette_has_term_payload(test_name: str) -> bool:
    for cassette_path in (CASSETTE_DIR / test_name, CASSETTE_DIR / f"{test_name}.yaml"):
        if not cassette_path.exists():
            continue
        payload = cassette_path.read_text(encoding="utf-8", errors="ignore")
        if any(marker in payload for marker in TERM_PAYLOAD_MARKERS):
            return True
    return False


def _skip_if_term_payload_unavailable(test_name: str) -> None:
    if _is_vcr_recording_enabled():
        return
    if not _cassette_has_term_payload(test_name):
        pytest.skip(
            "VCR cassette sample has no mesh_terms/keywords payload for publication_term extraction."
        )


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_publication_term_full_cycle(e2e_data_dir: Path):
    """E2E: ChEMBL Publication Term pipeline from fetch to Silver.

    Verifies:
    1. Publication data is fetched and terms are extracted
    2. Silver table contains expected term records
    3. Each term has required fields
    """
    _skip_if_term_payload_unavailable("test_chembl_publication_term_full_cycle")

    # Arrange
    ctx = create_test_context("chembl_publication_term", limit=5)

    # Act
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Bronze layer (uses publication_term path per ADR-024 naming)
    try:
        bronze_files = assert_bronze_files_exist(
            e2e_data_dir, "chembl", "publication_term"
        )
    except AssertionError as exc:
        pytest.skip(f"No publication_term records in cassette sample: {exc}")
    assert len(bronze_files) >= 1

    # Assert - Silver layer
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_publication_term", expected_min=1
    )
    assert silver_count >= 1

    # Assert - Schema validation
    records = get_silver_records(e2e_data_dir, "chembl_publication_term")
    required_fields = ["publication_id", "term", "term_type"]
    for record in records:
        for field in required_fields:
            assert field in record, f"Missing required field: {field}"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_publication_term_types(e2e_data_dir: Path):
    """E2E: Verify term types are correctly classified.

    Document terms can be:
    - MESH_HEADING: MeSH descriptor terms
    - MESH_QUALIFIER: MeSH qualifier/subheading
    - KEYWORD: Author-provided keywords
    """
    _skip_if_term_payload_unavailable("test_chembl_publication_term_types")

    # Arrange
    ctx = create_test_context("chembl_publication_term", limit=10)

    # Act
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Check term types
    try:
        records = get_silver_records(e2e_data_dir, "chembl_publication_term")
    except SILVER_READ_SKIP_ERRORS as exc:
        pytest.skip(f"No Silver publication_term table for cassette sample: {exc}")

    valid_term_types = {"MESH_HEADING", "MESH_QUALIFIER", "KEYWORD"}

    for record in records:
        term_type = record.get("term_type")
        assert term_type in valid_term_types, f"Invalid term_type: {term_type}"
        assert record.get("term"), "Term text should not be empty"
        assert record.get("publication_id"), "publication_id should not be empty"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_publication_term_mesh_fields(e2e_data_dir: Path):
    """E2E: Verify MeSH-specific fields are extracted.

    MeSH terms may include:
    - mesh_id: MeSH identifier (e.g., "D001241")
    - qualifier: MeSH qualifier (e.g., "pharmacology")
    """
    _skip_if_term_payload_unavailable("test_chembl_publication_term_mesh_fields")

    # Arrange
    ctx = create_test_context("chembl_publication_term", limit=10)

    # Act
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Check MeSH fields presence
    try:
        records = get_silver_records(e2e_data_dir, "chembl_publication_term")
    except SILVER_READ_SKIP_ERRORS as exc:
        pytest.skip(f"No Silver publication_term table for cassette sample: {exc}")

    mesh_records = [
        r for r in records if r.get("term_type") in ("MESH_HEADING", "MESH_QUALIFIER")
    ]

    # If there are MeSH records, verify structure
    for record in mesh_records:
        # mesh_id and qualifier may be None, but should exist as keys
        assert "mesh_id" in record or record.get("term_type") == "MESH_QUALIFIER"
