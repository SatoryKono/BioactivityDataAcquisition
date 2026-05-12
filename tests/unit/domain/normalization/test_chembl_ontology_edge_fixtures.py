"""Normalization tests for tracked ChEMBL ontology edge fixtures."""

from __future__ import annotations

from typing import Any

import pytest

from bioetl.domain.normalization.profiles import resolve_normalization_profile

_ASSAY_EDGE_ROWS: list[dict[str, Any]] = [
    {
        "assay_chembl_id": "CHEMBL_EDGE_BAO_1",
        "bao_format": "bao:0000190",
        "bao_label": "assay format",
    },
    {
        "assay_chembl_id": "CHEMBL_EDGE_BAO_2",
        "bao_format": "BAO_0000219",
        "bao_label": "cell-based format",
    },
]

_CELL_LINE_EDGE_ROWS: list[dict[str, Any]] = [
    {
        "cell_chembl_id": "CHEMBL3307999",
        "cellosaurus_id": "cvcl:4704",
        "clo_id": "clo:0003684",
        "efo_id": "efo:0002312",
    },
    {
        "cell_chembl_id": "CHEMBL3307998",
        "cellosaurus_id": "CVCL_2676",
        "clo_id": "CLO_0008331",
        "efo_id": "EFO_0002312",
    },
]

_TISSUE_EDGE_ROWS: list[dict[str, Any]] = [
    {
        "tissue_chembl_id": "CHEMBL3988991",
        "bto_id": "bto:0000142",
        "efo_id": "efo_0000408",
        "uberon_id": "uberon:0002107",
    },
    {
        "tissue_chembl_id": "CHEMBL3988992",
        "bto_id": "BTO_0000840",
        "efo_id": "EFO:0000856",
        "uberon_id": "UBERON_0000004",
    },
]


def _project_rows(
    rows: list[dict[str, Any]],
    *,
    fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    return [{field: row.get(field) for field in fields} for row in rows]


def _normalize_rows(
    *,
    entity_type: str,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    profile = resolve_normalization_profile("chembl", entity_type)
    assert profile is not None
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        normalized_row = {}
        for field, value in row.items():
            rule = profile.rule_for(field)
            normalized_row[field] = value if rule is None else rule.apply(value, record=row)
        normalized_rows.append(normalized_row)
    return normalized_rows


@pytest.mark.unit
def test_chembl_assay_ontology_edge_fixture_normalizes_bao_namespace_variants() -> None:
    rows = _project_rows(
        _ASSAY_EDGE_ROWS,
        fields=(
            "bao_format",
            "bao_label",
            "bao_format_iri",
            "bao_format_mapping_status",
        ),
    )

    normalized = _normalize_rows(entity_type="assay", rows=rows)

    assert normalized[0]["bao_format"] == "BAO_0000190"
    assert normalized[0]["bao_format_mapping_status"] == "mapped"
    assert (
        normalized[0]["bao_format_iri"] == "https://purl.obolibrary.org/obo/BAO_0000190"
    )
    assert normalized[1]["bao_format"] == "BAO_0000219"
    assert normalized[1]["bao_format_mapping_status"] == "mapped"


@pytest.mark.unit
def test_chembl_cell_line_ontology_edge_fixture_normalizes_namespace_variants() -> None:
    rows = _project_rows(
        _CELL_LINE_EDGE_ROWS,
        fields=(
            "clo_id",
            "efo_id",
            "cellosaurus_id",
            "clo_mapping_status",
            "efo_mapping_status",
        ),
    )

    normalized = _normalize_rows(entity_type="cell_line", rows=rows)

    assert normalized[0]["clo_id"] == "CLO_0003684"
    assert normalized[0]["efo_id"] == "EFO_0002312"
    assert normalized[0]["clo_mapping_status"] == "mapped"
    assert normalized[0]["efo_mapping_status"] == "mapped"
    assert normalized[1]["clo_id"] == "CLO_0008331"
    assert normalized[1]["efo_id"] == "EFO_0002312"


@pytest.mark.unit
def test_chembl_tissue_ontology_edge_fixture_normalizes_namespace_variants() -> None:
    rows = _project_rows(
        _TISSUE_EDGE_ROWS,
        fields=(
            "bto_id",
            "efo_id",
            "uberon_id",
            "bto_mapping_status",
            "efo_mapping_status",
            "uberon_mapping_status",
        ),
    )

    normalized = _normalize_rows(entity_type="tissue", rows=rows)

    assert normalized[0]["bto_id"] == "BTO_0000142"
    assert normalized[0]["efo_id"] == "EFO_0000408"
    assert normalized[0]["uberon_id"] == "UBERON_0002107"
    assert normalized[0]["bto_mapping_status"] == "mapped"
    assert normalized[0]["efo_mapping_status"] == "mapped"
    assert normalized[0]["uberon_mapping_status"] == "mapped"
    assert normalized[1]["bto_id"] == "BTO_0000840"
    assert normalized[1]["efo_id"] == "EFO_0000856"
    assert normalized[1]["uberon_id"] == "UBERON_0000004"
