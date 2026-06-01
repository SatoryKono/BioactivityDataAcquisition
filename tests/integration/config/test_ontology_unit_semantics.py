"""Contract checks for ontology and unit semantic role separation."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml

from scripts.engineering.qa.check_ontology_unit_semantics import (
    DEFAULT_ROLE_REGISTRY,
    validate_ontology_unit_semantics,
)


pytestmark = pytest.mark.integration

def test_ontology_unit_semantics_gate_passes_current_repo() -> None:
    findings = validate_ontology_unit_semantics(repo_root=Path("."))

    assert not findings, "\n".join(finding.message for finding in findings)


def test_role_registry_defines_measurement_and_ontology_role_families() -> None:
    payload = yaml.safe_load(DEFAULT_ROLE_REGISTRY.read_text(encoding="utf-8"))

    measurement_ids = {
        family["family_id"] for family in payload["measurement_role_families"]
    }
    ontology_ids = {family["family_id"] for family in payload["ontology_role_families"]}

    assert "chembl_activity_measurement_unit_roles" in measurement_ids
    assert {
        "chembl_activity_bao_endpoint_roles",
        "chembl_activity_bao_format_roles",
        "chembl_activity_uo_unit_roles",
        "chembl_activity_qudt_unit_roles",
        "chembl_assay_bao_format_roles",
        "chembl_tissue_bto_roles",
        "chembl_tissue_efo_roles",
        "chembl_tissue_uberon_roles",
        "chembl_cell_line_clo_roles",
        "chembl_cell_line_efo_roles",
    } <= ontology_ids


def test_measurement_roles_keep_raw_standardized_and_ontology_fields_separate() -> None:
    payload = yaml.safe_load(DEFAULT_ROLE_REGISTRY.read_text(encoding="utf-8"))
    measurement = payload["measurement_role_families"][0]
    role_fields = measurement["field_roles"]

    assert role_fields["raw_unit_text"] == "units"
    assert role_fields["standardized_unit_code"] == "standard_units"
    assert role_fields["measurement_type"] == "standard_type"
    assert role_fields["standardized_value"] == "standard_value"
    assert len(set(role_fields.values())) == len(role_fields)
