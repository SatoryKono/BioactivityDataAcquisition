"""Tests for assay organism classification."""

from bioetl.domain.mapping.organism_classification import (
    OrganismClass,
    classify_organism,
    normalize_organism_name,
)


def test_taxonomy_id_priority_for_multicellular() -> None:
    result = classify_organism("Homo sapiens", 9606)

    assert result.organism_class == OrganismClass.MULTICELLULAR
    assert result.source == "taxonomy_id"
    assert result.source_conflict is False


def test_virus_and_phage_are_acellular() -> None:
    hiv = classify_organism("hiv", 11676)
    phage = classify_organism("Enterobacteria phage lambda", 10710)

    assert hiv.organism_class == OrganismClass.ACELLULAR
    assert phage.organism_class == OrganismClass.ACELLULAR


def test_microorganisms_are_unicellular() -> None:
    e_coli = classify_organism("Escherichia coli", 562)
    candida = classify_organism("Candida albicans", 5476)

    assert e_coli.organism_class == OrganismClass.UNICELLULAR
    assert candida.organism_class == OrganismClass.UNICELLULAR


def test_alias_resolution_by_name_when_taxonomy_id_missing() -> None:
    rice = classify_organism("rice", None)
    monkey = classify_organism("monkey", None)

    assert rice.organism_class == OrganismClass.MULTICELLULAR
    assert rice.source == "organism_name"
    assert monkey.organism_class == OrganismClass.MULTICELLULAR


def test_alias_eel_prefers_taxonomy_id() -> None:
    result = classify_organism("eel", 8005)

    assert result.organism_class == OrganismClass.MULTICELLULAR
    assert result.source == "taxonomy_id"


def test_conflict_marks_source_conflict_but_uses_taxonomy_id() -> None:
    result = classify_organism("Escherichia coli", 9606)

    assert result.organism_class == OrganismClass.MULTICELLULAR
    assert result.source == "taxonomy_id"
    assert result.source_conflict is True
    assert result.reason is not None


def test_normalization_removes_parentheses_and_supports_strain_prefix() -> None:
    normalized = normalize_organism_name("  Streptococcus pneumoniae (TIGR4)  ")
    result = classify_organism("Plasmodium falciparum 3D7", None)

    assert normalized == "streptococcus pneumoniae"
    assert result.organism_class == OrganismClass.UNICELLULAR


def test_invalid_taxonomy_falls_back_to_name() -> None:
    result = classify_organism("Influenza A virus (A/Puerto Rico/8/1934(H1N1))", "N/A")

    assert result.organism_class == OrganismClass.ACELLULAR
    assert result.source == "organism_name"
    assert result.reason is not None


def test_empty_input_is_unresolved() -> None:
    result = classify_organism("   ", None)

    assert result.organism_class is None
    assert result.source == "unresolved"
    assert result.reason is not None
