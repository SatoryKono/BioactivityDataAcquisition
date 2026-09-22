"""Offline upstream acceptance using checked-in ChEMBL response records."""

import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from deltalake import DeltaTable

from bioetl.composition.bootstrap import bootstrap_pipeline_runner
from .conftest import create_test_context


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("entity", "resource", "collection"),
    [
        ("protein_class", "protein_classification", "protein_classifications"),
        ("target_component", "target_component", "target_components"),
    ],
)
async def test_classification_upstream_materializes_gold(
    e2e_data_dir: Path,
    respx_mock,
    entity,
    resource,
    collection,
):
    """Exercise extraction, transforms and physical Gold writes with real fixtures."""
    fixture = (
        Path("tests/fixtures/bronze/chembl") / entity / "sample_ci_2026-04-29.jsonl"
    )
    records = [json.loads(line) for line in fixture.read_text().splitlines()][:5]
    base = "https://www.ebi.ac.uk/chembl/api/data/"
    respx_mock.get(base + "status").mock(
        return_value=httpx.Response(200, json={"status": "UP"})
    )
    route = respx_mock.get(base + resource).mock(
        return_value=httpx.Response(
            200,
            json={collection: records, "page_meta": {"next": None}},
        )
    )
    context = create_test_context("chembl_" + entity, limit=len(records))
    context = replace(
        context,
        required_persistence_profile="degraded_observable",
        required_persistence_profile_opt_down=True,
    )
    runner = bootstrap_pipeline_runner(context)
    await runner.run()
    assert route.called, "Extraction must actually request the upstream collection"
    for layer in ("silver", "gold"):
        table = DeltaTable(str(e2e_data_dir / "output" / layer / "chembl" / entity))
        rows = table.to_pyarrow_table()
        # The synthetic root is deliberately excluded; all real classes survive.
        assert rows.num_rows == len(records) - (1 if entity == "protein_class" else 0)
        if entity == "protein_class":
            assert rows.column("parent_id").to_pylist() == [0] * rows.num_rows
