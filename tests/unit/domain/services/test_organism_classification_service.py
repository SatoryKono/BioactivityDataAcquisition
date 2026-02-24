"""Unit tests for organism classification service."""

from __future__ import annotations

import pytest

from bioetl.domain.services.organism_classification_service import (
    OrganismClass,
    classify_organism,
)


@pytest.mark.parametrize(
    ("organism", "taxonomy_id", "expected_class", "expected_source"),
    [
        (
            "Human immunodeficiency virus 1",
            11676,
            OrganismClass.ACELLULAR,
            "taxonomy_id",
        ),
        (
            "Influenza A virus (A/duck/Alberta/35/76(H1N1))",
            211044,
            OrganismClass.ACELLULAR,
            "taxonomy_id",
        ),
        ("Enterobacteria phage lambda", 10710, OrganismClass.ACELLULAR, "taxonomy_id"),
        ("Escherichia coli", 562, OrganismClass.UNICELLULAR, "taxonomy_id"),
        ("Staphylococcus aureus", 1280, OrganismClass.UNICELLULAR, "taxonomy_id"),
        ("Candida albicans", 5476, OrganismClass.UNICELLULAR, "taxonomy_id"),
        ("Homo sapiens", 9606, OrganismClass.MULTICELLULAR, "taxonomy_id"),
        ("Rattus norvegicus", 10116, OrganismClass.MULTICELLULAR, "taxonomy_id"),
        ("Glycine max", 3847, OrganismClass.MULTICELLULAR, "taxonomy_id"),
    ],
)
def test_classification_by_taxonomy_id(
    organism: str,
    taxonomy_id: int,
    expected_class: OrganismClass,
    expected_source: str,
) -> None:
    """Known mapped taxonomy IDs should classify deterministically."""
    result = classify_organism(organism, taxonomy_id)

    assert result.organism_class == expected_class
    assert result.source == expected_source
    assert result.taxonomy_id == taxonomy_id


@pytest.mark.parametrize(
    ("organism", "taxonomy_id", "expected_normalized", "expected_class"),
    [
        ("hiv", None, "human immunodeficiency virus 1", OrganismClass.ACELLULAR),
        (" eel ", None, "anguilla anguilla", OrganismClass.MULTICELLULAR),
        ("rice", None, "oryza sativa japonica group", OrganismClass.MULTICELLULAR),
        ("monkey", None, "catarrhini", OrganismClass.MULTICELLULAR),
        (
            "Plasmodium falciparum 3D7 (isolate)",
            None,
            "plasmodium falciparum",
            OrganismClass.UNICELLULAR,
        ),
    ],
)
def test_alias_and_normalization_resolution(
    organism: str,
    taxonomy_id: int | None,
    expected_normalized: str,
    expected_class: OrganismClass,
) -> None:
    """Name-based path should normalize aliases and strain annotations."""
    result = classify_organism(organism, taxonomy_id)

    assert result.normalized_organism == expected_normalized
    assert result.organism_class == expected_class
    assert result.source == "organism_name"


def test_taxonomy_id_priority_on_conflict_sets_diagnostics() -> None:
    """taxonomy_id must win when organism_name disagrees."""
    result = classify_organism("Escherichia coli", 9606)

    assert result.organism_class == OrganismClass.MULTICELLULAR
    assert result.source == "taxonomy_id"
    assert result.source_conflict is True
    assert result.reason is not None


@pytest.mark.parametrize(
    ("organism", "taxonomy_id", "reason_fragment"),
    [
        (None, None, "unable to classify"),
        ("", "", "unable to classify"),
        ("Unknown species", None, "unable to classify"),
        ("Unknown species", "not-an-int", "unable to classify"),
    ],
)
def test_unresolved_for_invalid_or_empty_input(
    organism: str | None,
    taxonomy_id: str | int | None,
    reason_fragment: str,
) -> None:
    """Empty/invalid/unmapped inputs should be unresolved with explanation."""
    result = classify_organism(organism, taxonomy_id)

    assert result.organism_class is None
    assert result.source == "unresolved"
    assert result.reason is not None
    assert reason_fragment in result.reason


def test_valid_but_unmapped_taxonomy_id_is_unresolved() -> None:
    """Valid taxonomy ID without a table entry should be unresolved."""
    result = classify_organism("any", 123456)

    assert result.taxonomy_id == 123456
    assert result.organism_class is None
    assert result.source == "unresolved"
    assert result.reason == "taxonomy_id 123456 is valid but not mapped"
