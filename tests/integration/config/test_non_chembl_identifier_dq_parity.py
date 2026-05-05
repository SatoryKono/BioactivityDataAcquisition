"""Parity checks for string-backed non-ChEMBL identifier DQ rules."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


pytestmark = pytest.mark.integration


def _load_entity_config(provider: str) -> dict[str, object]:
    path = Path("configs/entities") / provider / "publication.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _field_validation(provider: str, field_name: str) -> dict[str, object]:
    validations = _load_entity_config(provider)["quality"]["entity_field_validations"]
    for rule in validations:
        if rule.get("field") == field_name:
            return rule
    raise AssertionError(f"{provider}.publication missing validation for {field_name}")


def test_openalex_semanticscholar_and_pubmed_pmid_rules_use_string_pattern_contract() -> (
    None
):
    for provider in ("openalex", "semanticscholar", "pubmed"):
        rule = _field_validation(provider, "pmid")
        assert rule["type"] == "pattern"
        assert rule["pattern"] == r"^[1-9]\d{0,9}$"
