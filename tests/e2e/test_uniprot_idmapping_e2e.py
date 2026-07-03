"""E2E tests for UniProt ID-mapping pipeline normalization seams."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from .conftest import (
    assert_bronze_files_exist,
    assert_silver_table_has_records,
    create_test_context,
    get_silver_records,
    run_pipeline_or_skip_transient,
)

pytestmark = pytest.mark.usefixtures("relaxed_dq_env")


@pytest.fixture
def vcr_cassette_name() -> str:
    """Reuse the shipped UniProt ID-mapping cassette for deterministic playback."""
    return "TestUniProtIDMappingIntegration.test_map_single_id"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_uniprot_idmapping_full_cycle_normalizes_mapping_gate_fields(
    e2e_data_dir: Path,
) -> None:
    """E2E: UniProt ID mapping should emit canonical chained-enrichment anchors."""
    ctx = create_test_context(
        "uniprot_idmapping",
        limit=1,
        filter_ids=("CHEMBL204",),
        filter_field="target_id",
    )

    await run_pipeline_or_skip_transient(ctx)

    bronze_files = assert_bronze_files_exist(e2e_data_dir, "uniprot", "idmapping")
    assert len(bronze_files) >= 1

    silver_count = await assert_silver_table_has_records(
        e2e_data_dir, "uniprot_idmapping", expected_min=1
    )
    assert silver_count >= 1

    records = await get_silver_records(e2e_data_dir, "uniprot_idmapping")
    matched = [record for record in records if record.get("target_id") == "CHEMBL204"]
    assert matched, "Expected CHEMBL204 row in uniprot_idmapping Silver output"

    record = matched[0]
    assert record["mapping_status"] == "found"
    assert record["target_id"] == "CHEMBL204"
    assert record["uniprot_accession"] is not None
    assert re.fullmatch(r"[A-Z0-9]{6,10}", str(record["uniprot_accession"]))
    assert record["_dq_warn"] is False

    taxonomy_id = record.get("taxonomy_id")
    if taxonomy_id is not None:
        assert taxonomy_id == 9606

    all_mappings = record.get("all_mappings")
    if all_mappings is not None:
        assert record["uniprot_accession"] in str(all_mappings)
