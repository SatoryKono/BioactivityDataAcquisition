"""Parity guards and synthetic drift checks for #12029.

The registry, the reference-identifier summary, fixture sections, and
normalizer keys must move together. A copied surface with one removed or
extra token fails the same comparison the live files pass.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.domain.normalization._reference_id_registry import (
    _REFERENCE_IDENTIFIER_FAMILY_SPECS,
    build_reference_identifier_families,
)
from bioetl.domain.normalization.reference_ids import reference_identifier_families

pytestmark = pytest.mark.architecture

_SUMMARY_DOC = Path("docs/04-reference/normalization/reference-identifiers.md")
_FIXTURE = Path("tests/fixtures/normalization/non_chembl_identifier_cases.yaml")
_FIXTURE_SECTIONS = (
    "publication_identifier_arrays",
    "pubchem_identifier_fields",
    "uniprot_identifier_arrays",
    "publication_raw_type_policy",
    "publication_oa_status_policy",
    "publication_structured_field_policy",
    "publication_taxonomy_policy",
    "composite_publication_join_keys",
    "composite_molecule_join_keys",
    "composite_target_join_keys",
)


def summary_family_names(text: str) -> set[str]:
    """Return family names from the markdown summary table."""
    names: set[str] = set()
    in_table = False
    for line in text.splitlines():
        if line.startswith("## Family Summary"):
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if not in_table or not line.startswith("| `"):
            continue
        names.add(line.split("`", 2)[1])
    return names


def registry_family_names() -> set[str]:
    return {family.name for family in reference_identifier_families()}


def _normalizer_keys() -> dict[str, None]:
    return {spec[3]: None for spec in _REFERENCE_IDENTIFIER_FAMILY_SPECS if spec[3]}


def test_reference_identifier_summary_matches_registry() -> None:
    documented = summary_family_names(_SUMMARY_DOC.read_text(encoding="utf-8"))
    assert documented == registry_family_names()


def test_summary_drift_is_rejected() -> None:
    text = _SUMMARY_DOC.read_text(encoding="utf-8")
    removed = text.replace("| `doi` |", "| `not_a_family` |", 1)
    documented = summary_family_names(removed)
    assert "doi" in registry_family_names() - documented
    assert "not_a_family" in documented - registry_family_names()


def test_fixture_sections_are_enumerated() -> None:
    payload = yaml.safe_load(_FIXTURE.read_text(encoding="utf-8"))
    assert tuple(payload) == _FIXTURE_SECTIONS


def test_fixture_section_drift_is_rejected() -> None:
    payload = yaml.safe_load(_FIXTURE.read_text(encoding="utf-8"))
    payload["unlisted_section"] = {}
    assert tuple(payload) != _FIXTURE_SECTIONS


def test_extra_normalizer_key_is_rejected() -> None:
    mapping = _normalizer_keys()
    mapping["unused_key"] = None
    with pytest.raises(ValueError, match="Unexpected extra normalizer keys"):
        build_reference_identifier_families(mapping)


def test_missing_normalizer_key_is_rejected() -> None:
    mapping = _normalizer_keys()
    del mapping["doi"]
    with pytest.raises(ValueError, match="Missing required normalizer keys"):
        build_reference_identifier_families(mapping)
