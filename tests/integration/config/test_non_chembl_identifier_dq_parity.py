"""Parity checks for governed non-ChEMBL OA and identifier DQ rules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml


pytestmark = pytest.mark.integration


def _load_entity_config(provider: str, entity: str) -> dict[str, Any]:
    path = Path("configs/entities") / provider / f"{entity}.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _field_validation(provider: str, entity: str, field_name: str) -> dict[str, Any]:
    validations = _load_entity_config(provider, entity)["quality"][
        "entity_field_validations"
    ]
    for rule in validations:
        if rule.get("field") == field_name:
            return rule
    raise AssertionError(f"{provider}.{entity} missing validation for {field_name}")


def _allowed_values(rule: dict[str, Any]) -> list[str]:
    values = rule.get("allowed_values") or rule.get("allowed") or ()
    return [str(value) for value in values]


def test_openalex_semanticscholar_and_pubmed_pmid_rules_use_string_pattern_contract() -> (
    None
):
    for provider in ("openalex", "semanticscholar", "pubmed"):
        rule = _field_validation(provider, "publication", "pmid")
        assert rule["type"] == "pattern"
        assert rule["pattern"] == r"^[1-9]\d{0,9}$"


def test_governed_publication_oa_status_rules_match_shared_registry() -> None:
    expected = ["gold", "green", "hybrid", "bronze", "closed"]

    for provider in ("openalex", "semanticscholar"):
        rule = _field_validation(provider, "publication", "oa_status")
        assert rule["type"] == "enum"
        assert _allowed_values(rule) == expected


def test_governed_publication_identifier_arrays_publish_canonical_json_patterns() -> (
    None
):
    expected_patterns = {
        ("crossref", "publication", "author_orcids"): (
            r'^\[("\d{4}-\d{4}-\d{4}-[0-9X]"(,"\d{4}-\d{4}-\d{4}-[0-9X]")*)?\]$'
        ),
        ("crossref", "publication", "issn_list"): (
            r'^\[(\"[0-9Xx-]+\"(,\"[0-9Xx-]+\")*)?\]$'
        ),
        ("openalex", "publication", "author_openalex_ids"): (
            r'^\[("A\d+"(,"A\d+")*)?\]$'
        ),
        ("openalex", "publication", "author_orcids"): (
            r'^\[("\d{4}-\d{4}-\d{4}-[0-9X]"(,"\d{4}-\d{4}-\d{4}-[0-9X]")*)?\]$'
        ),
        ("openalex", "publication", "institution_ids"): (
            r'^\[("I\d+"(,"I\d+")*)?\]$'
        ),
        ("openalex", "publication", "ror_ids"): (
            r'^\[("https://ror\.org/[a-z0-9]+"(,"https://ror\.org/[a-z0-9]+")*)?\]$'
        ),
        ("openalex", "publication", "issn_list"): (
            r'^\[("[0-9Xx-]+"(,"[0-9Xx-]+")*)?\]$'
        ),
        ("pubmed", "publication", "author_orcids"): (
            r'^\[("\d{4}-\d{4}-\d{4}-[0-9X]"(,"\d{4}-\d{4}-\d{4}-[0-9X]")*)?\]$'
        ),
        ("pubmed", "publication", "issn_list"): (
            r'^\[("[0-9Xx-]+"(,"[0-9Xx-]+")*)?\]$'
        ),
        ("semanticscholar", "publication", "author_s2_ids"): (
            r'^\[("[0-9a-f]{40}"(,"[0-9a-f]{40}")*)?\]$'
        ),
        ("semanticscholar", "publication", "author_orcids"): (
            r'^\[("\d{4}-\d{4}-\d{4}-[0-9X]"(,"\d{4}-\d{4}-\d{4}-[0-9X]")*)?\]$'
        ),
        ("semanticscholar", "publication", "issn_list"): (
            r'^\[("[0-9Xx-]+"(,"[0-9Xx-]+")*)?\]$'
        ),
        ("uniprot", "idmapping", "all_mappings"): (
            r'^\[("[A-Za-z0-9:/._-]+"(,"[A-Za-z0-9:/._-]+")*)?\]$'
        ),
    }

    for key, pattern in expected_patterns.items():
        rule = _field_validation(*key)
        assert rule["type"] == "pattern"
        assert rule["pattern"] == pattern
