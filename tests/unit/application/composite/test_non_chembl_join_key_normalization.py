"""Golden tests for non-ChEMBL composite join-key normalization."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.application.composite.join_key_normalization import stringify_join_key_value

pytestmark = pytest.mark.repo_backed

FIXTURE_PATH = Path("tests/fixtures/normalization/non_chembl_identifier_cases.yaml")


def _load_cases() -> dict[str, Any]:
    payload = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.mark.unit
@pytest.mark.parametrize(
    "section",
    (
        "composite_publication_join_keys",
        "composite_molecule_join_keys",
        "composite_target_join_keys",
    ),
)
def test_non_chembl_composite_join_key_cases_stringify_to_canonical_values(
    section: str,
) -> None:
    cases = _load_cases()

    for case in cases[section].values():
        key = case.get("key")
        raw_values = case.get("raw_values")
        expected = case.get("expected")
        if not isinstance(key, str) or not isinstance(raw_values, list):
            continue

        canonical_values = {
            stringify_join_key_value(raw_value, key=key) for raw_value in raw_values
        }
        assert canonical_values == {expected}


@pytest.mark.unit
def test_molecule_join_key_fixture_matches_pubchem_anchor_boundary_contract() -> None:
    cases = _load_cases()
    molecule_case = cases["composite_molecule_join_keys"]["pubchem_anchor_boundary"]
    config = yaml.safe_load(
        Path("configs/composites/molecule.yaml").read_text(encoding="utf-8")
    )
    policy = config["composite"]["normalized_anchor_policy"]["pubchem_compound"][
        "join_boundary"
    ]

    assert policy["active_join_keys"] == molecule_case["active_join_keys"]
    assert (
        policy["retained_validation_anchors"]
        == molecule_case["retained_validation_anchors"]
    )


@pytest.mark.unit
def test_target_join_key_fixture_matches_uniprot_mapping_gate_contract() -> None:
    cases = _load_cases()
    target_case = cases["composite_target_join_keys"]["uniprot_mapping_gate"]
    config = yaml.safe_load(
        Path("configs/composites/target.yaml").read_text(encoding="utf-8")
    )
    policy = config["composite"]["normalized_anchor_policy"]["uniprot_idmapping"][
        "join_boundary"
    ]

    assert policy["source_anchor"] == target_case["source_anchor"]
    assert policy["normalized_output_anchor"] == target_case["normalized_output_anchor"]
    assert policy["required_status"] == target_case["required_status"]
