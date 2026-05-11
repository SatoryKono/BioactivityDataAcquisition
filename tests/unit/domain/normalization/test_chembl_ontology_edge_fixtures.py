"""Normalization tests for tracked ChEMBL ontology edge fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)

ROOT = Path(".")
MANIFEST_PATH = ROOT / "configs" / "base" / "bronze_fixture_manifest.yaml"


def _load_manifest() -> dict[str, dict[str, Any]]:
    payload = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    fixtures = payload.get("fixtures")
    assert isinstance(fixtures, dict)
    return {
        str(key): value for key, value in fixtures.items() if isinstance(value, dict)
    }


def _edge_fixture_rows(fixture_key: str) -> list[dict[str, Any]]:
    manifest = _load_manifest()
    edge_fixtures = manifest[fixture_key].get("edge_fixtures")
    assert isinstance(edge_fixtures, list) and edge_fixtures
    edge_fixture = edge_fixtures[0]
    assert isinstance(edge_fixture, dict)
    path = ROOT / str(edge_fixture["fixture_path"])
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _project_rows(
    rows: list[dict[str, Any]],
    *,
    fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    return [{field: row.get(field) for field in fields} for row in rows]


@pytest.mark.unit
def test_chembl_assay_ontology_edge_fixture_normalizes_bao_namespace_variants() -> None:
    processor = RecordNormalizationProcessor(provider="chembl", entity_type="assay")
    rows = _project_rows(
        _edge_fixture_rows("chembl/assay"),
        fields=("bao_format", "bao_label"),
    )

    normalized = [processor.normalize_business_data(row) for row in rows]

    assert normalized[0]["bao_format"] == "BAO_0000190"
    assert normalized[0]["bao_format_mapping_status"] == "mapped"
    assert (
        normalized[0]["bao_format_iri"] == "https://purl.obolibrary.org/obo/BAO_0000190"
    )
    assert normalized[1]["bao_format"] == "BAO_0000219"
    assert normalized[1]["bao_format_mapping_status"] == "mapped"


@pytest.mark.unit
def test_chembl_cell_line_ontology_edge_fixture_normalizes_namespace_variants() -> None:
    processor = RecordNormalizationProcessor(provider="chembl", entity_type="cell_line")
    rows = _project_rows(
        _edge_fixture_rows("chembl/cell_line"),
        fields=("clo_id", "efo_id", "cellosaurus_id"),
    )

    normalized = [processor.normalize_business_data(row) for row in rows]

    assert normalized[0]["clo_id"] == "CLO_0003684"
    assert normalized[0]["efo_id"] == "EFO_0002312"
    assert normalized[0]["clo_mapping_status"] == "mapped"
    assert normalized[0]["efo_mapping_status"] == "mapped"
    assert normalized[1]["clo_id"] == "CLO_0008331"
    assert normalized[1]["efo_id"] == "EFO_0002312"


@pytest.mark.unit
def test_chembl_tissue_ontology_edge_fixture_normalizes_namespace_variants() -> None:
    processor = RecordNormalizationProcessor(provider="chembl", entity_type="tissue")
    rows = _project_rows(
        _edge_fixture_rows("chembl/tissue"),
        fields=("bto_id", "efo_id", "uberon_id"),
    )

    normalized = [processor.normalize_business_data(row) for row in rows]

    assert normalized[0]["bto_id"] == "BTO_0000142"
    assert normalized[0]["efo_id"] == "EFO_0000408"
    assert normalized[0]["uberon_id"] == "UBERON_0002107"
    assert normalized[0]["bto_mapping_status"] == "mapped"
    assert normalized[0]["efo_mapping_status"] == "mapped"
    assert normalized[0]["uberon_mapping_status"] == "mapped"
    assert normalized[1]["bto_id"] == "BTO_0000840"
    assert normalized[1]["efo_id"] == "EFO_0000856"
    assert normalized[1]["uberon_id"] == "UBERON_0000004"
