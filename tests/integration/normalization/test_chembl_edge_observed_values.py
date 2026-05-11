"""Offline edge-case checks for ChEMBL ontology/reference Bronze fixtures."""

from __future__ import annotations

import json
from pathlib import Path


def _load_jsonl(path: str) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_chembl_activity_edge_fixture_covers_bao_uo_and_qudt_variants() -> None:
    rows = _load_jsonl(
        "tests/fixtures/bronze/chembl/activity/sample_edge_ontology_units_2026-05-11.jsonl"
    )

    assert {row["bao_format"] for row in rows} == {"bao:0000190", "BAO_0000218"}
    assert {row["uo_units"] for row in rows} == {"UO:0000065", "UO_0000064"}
    assert {row["qudt_units"] for row in rows} == {"nM", "mg.kg-1"}


def test_chembl_cell_line_edge_fixture_covers_cellosaurus_clo_efo_and_taxonomy() -> None:
    rows = _load_jsonl(
        "tests/fixtures/bronze/chembl/cell_line/sample_edge_ontology_ids_2026-05-11.jsonl"
    )

    assert {"cvcl:0030", "CVCL_0031"} == {row["cellosaurus_id"] for row in rows}
    assert {"clo:0003684", "CLO_0003685"} == {row["clo_id"] for row in rows}
    assert {"efo:0001187", "EFO_0001188"} == {row["efo_id"] for row in rows}
    assert {9606, 10090} == {row["cell_source_tax_id"] for row in rows}


def test_chembl_tissue_edge_fixture_covers_bto_caloha_efo_and_uberon_variants() -> (
    None
) -> None:
    rows = _load_jsonl(
        "tests/fixtures/bronze/chembl/tissue/sample_edge_ontology_ids_2026-05-11.jsonl"
    )

    assert {"bto:0000142", "BTO_0000147"} == {row["bto_id"] for row in rows}
    assert {"CALOHA:TS-0284", "TS-9001"} == {row["caloha_id"] for row in rows}
    assert {"efo:0000400", "EFO_0000500"} == {row["efo_id"] for row in rows}
    assert {"uberon:0002107", "UBERON_0002113"} == {row["uberon_id"] for row in rows}


def test_chembl_target_component_edge_fixture_covers_accession_taxonomy_and_nested_reference_namespaces() -> (
    None
) -> None:
    rows = _load_jsonl(
        "tests/fixtures/bronze/chembl/target_component/sample_edge_reference_ids_2026-05-11.jsonl"
    )

    assert {"p12345", "Q9Y243"} == {row["accession"] for row in rows}
    assert {9606, 562} == {row["tax_id"] for row in rows}
    observed_sources = {
        xref["xref_src_db"]
        for row in rows
        for xref in row.get("target_component_xrefs", [])
    }
    assert {"UniProt", "GoFunction", "InterPro", "Pfam"} <= observed_sources
