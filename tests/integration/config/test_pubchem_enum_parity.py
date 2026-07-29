# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Parity checks for PubChem standardization enum-backed config surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.domain.normalization.chemical_standardization_contract import (
    CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    CHEMICAL_STANDARDIZATION_STATUSES,
)
from bioetl.domain.normalization.profiles.pubchem_compound import (
    PUBCHEM_COMPOUND_PROFILE,
)
from scripts.docs.generate_pipeline_normalization_field_matrix import (
    build_field_matrix_rows,
)

pytestmark = pytest.mark.integration

CONFIG_PATH = Path("configs/entities/pubchem/compound.yaml")
ENUM_PATH = Path("configs/enums/pubchem.yaml")
URN_VOCAB_PATH = Path("configs/vocab/pubchem_property_urn.yaml")
FIXTURE_PATH = Path("tests/fixtures/normalization/non_chembl_observed_values.yaml")
DOC_PATH = Path("docs/04-reference/normalization/pubchem-normalization.md")


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _entity_allowed_values(field_name: str) -> tuple[str, ...]:
    payload = _load_yaml(CONFIG_PATH)
    validations = payload["quality"]["entity_field_validations"]
    for rule in validations:
        if rule.get("field") == field_name:
            return tuple(str(value) for value in rule.get("allowed_values", ()))
    raise AssertionError(f"Missing validation for {field_name}")


def _matrix_row(field_name: str) -> dict[str, Any]:
    return next(
        row
        for row in build_field_matrix_rows()
        if row["pipeline_name"] == "pubchem_compound"
        and row["field_name"] == field_name
    )


def test_pubchem_standardization_status_parity_across_enum_config_profile_fixture_and_matrix() -> (
    None
):
    enum_payload = _load_yaml(ENUM_PATH)
    fixture_payload = _load_yaml(FIXTURE_PATH)
    expected_statuses = tuple(
        enum_payload["compound"]["chemical_standardization_statuses"]
    )

    assert expected_statuses == CHEMICAL_STANDARDIZATION_STATUSES
    assert (
        _entity_allowed_values("chemical_standardization_status") == expected_statuses
    )

    fixture_values = tuple(
        fixture_payload["pipelines"]["pubchem_compound"]["expected_controlled_values"][
            "chemical_standardization_status"
        ]
    )
    assert fixture_values == expected_statuses

    status_rule = PUBCHEM_COMPOUND_PROFILE.rule_for("chemical_standardization_status")
    assert status_rule is not None
    for value in expected_statuses:
        assert status_rule.apply(value.upper()) == value
    assert status_rule.apply("unexpected_status") is None

    matrix_row = _matrix_row("chemical_standardization_status")
    assert matrix_row["controlled_vocabulary_source"] == "configs/enums/pubchem.yaml"
    assert matrix_row["strictness"] == "strict_enum"


def test_pubchem_standardization_policy_version_parity_and_docs_note() -> None:
    enum_payload = _load_yaml(ENUM_PATH)
    expected_versions = tuple(
        enum_payload["compound"]["chemical_standardization_policy_versions"]
    )

    assert expected_versions == (CHEMICAL_STANDARDIZATION_POLICY_VERSION,)
    assert _entity_allowed_values("chemical_standardization_policy_version") == (
        CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    )

    policy_rule = PUBCHEM_COMPOUND_PROFILE.rule_for(
        "chemical_standardization_policy_version"
    )
    assert policy_rule is not None
    assert policy_rule.apply(CHEMICAL_STANDARDIZATION_POLICY_VERSION.upper()) == (
        CHEMICAL_STANDARDIZATION_POLICY_VERSION
    )
    assert policy_rule.apply("pubchem-basic-v2") is None

    matrix_row = _matrix_row("chemical_standardization_policy_version")
    assert matrix_row["controlled_vocabulary_source"] == "configs/enums/pubchem.yaml"
    assert matrix_row["strictness"] == "strict_enum"

    doc_text = DOC_PATH.read_text(encoding="utf-8")
    assert "chemical_standardization_policy_version" in doc_text
    assert "content_hash" in doc_text


def test_pubchem_property_urn_vocab_review_stays_governance_only() -> None:
    urn_vocab = _load_yaml(URN_VOCAB_PATH)
    matrix_rows = [
        row
        for row in build_field_matrix_rows()
        if row["pipeline_name"] == "pubchem_compound"
        and row["controlled_vocabulary_source"]
        == "configs/vocab/pubchem_property_urn.yaml"
    ]

    assert set(urn_vocab["fields"]) == {
        "datatype",
        "implementation",
        "label",
        "name",
        "release",
        "software",
        "source",
    }
    assert matrix_rows == []

    doc_text = DOC_PATH.read_text(encoding="utf-8")
    assert "no additional `props[].urn.*` vocabularies are promoted" in doc_text
