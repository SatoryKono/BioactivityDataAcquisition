"""Stable normalization golden fixtures for active Silver pipeline families."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.contract.silver_schemas.conftest import SILVER_SCHEMAS

ROOT = Path(__file__).resolve().parents[3]
GOLDEN_ROOT = ROOT / "tests" / "golden" / "normalization"

# Maps Silver schema registry keys to normalization golden fixture paths.
NORMALIZATION_GOLDEN_BY_SCHEMA: dict[str, Path] = {
    "chembl_activity": GOLDEN_ROOT / "chembl" / "activity.json",
    "chembl_molecule": GOLDEN_ROOT / "chembl" / "molecule.json",
    "chembl_publication": GOLDEN_ROOT / "chembl" / "publication.json",
    "chembl_target": GOLDEN_ROOT / "chembl" / "target.json",
    "chembl_target_component": GOLDEN_ROOT / "chembl" / "target_component.json",
    "pubchem_compound": GOLDEN_ROOT / "non_chembl" / "pubchem_compound.json",
    "uniprot_protein": GOLDEN_ROOT / "non_chembl" / "uniprot_protein.json",
    "uniprot_idmapping": GOLDEN_ROOT / "non_chembl" / "uniprot_idmapping.json",
    "pubmed_publication": GOLDEN_ROOT / "non_chembl" / "pubmed_publication.json",
    "crossref_publication": GOLDEN_ROOT / "non_chembl" / "crossref_publication.json",
    "openalex_publication": GOLDEN_ROOT / "non_chembl" / "openalex_publication.json",
    "semanticscholar_publication": (
        GOLDEN_ROOT / "non_chembl" / "semanticscholar_publication.json"
    ),
}

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]


@pytest.mark.parametrize("schema_name", sorted(NORMALIZATION_GOLDEN_BY_SCHEMA))
def test_normalization_golden_fixture_exists_for_active_schema(
    schema_name: str,
) -> None:
    """Every mapped Silver schema must have a committed normalization golden file."""
    assert schema_name in SILVER_SCHEMAS
    golden_path = NORMALIZATION_GOLDEN_BY_SCHEMA[schema_name]
    assert golden_path.exists(), f"Missing normalization golden: {golden_path}"


@pytest.mark.parametrize("schema_name", sorted(NORMALIZATION_GOLDEN_BY_SCHEMA))
def test_normalization_golden_payload_is_deterministic_shape(
    schema_name: str,
) -> None:
    """Normalization goldens must expose content_hash and sorted normalized payload."""
    golden_path = NORMALIZATION_GOLDEN_BY_SCHEMA[schema_name]
    payload = json.loads(golden_path.read_text(encoding="utf-8"))

    assert isinstance(payload.get("content_hash"), str) and len(payload["content_hash"]) == 64
    normalized = payload.get("normalized")
    assert isinstance(normalized, dict) and normalized
    assert list(normalized.keys()) == sorted(normalized.keys())
