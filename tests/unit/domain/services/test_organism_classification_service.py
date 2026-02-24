"""Unit tests for organism classification service."""

from bioetl.domain.services import (
    OrganismClass,
    classify_organism,
)


def test_classify_with_taxonomy_priority_multicellular() -> None:
    result = classify_organism("Homo sapiens", 9606)

    assert result.organism_class == OrganismClass.MULTICELLULAR
    assert result.source == "taxonomy_id"
    assert result.taxonomy_id == 9606
    assert result.source_conflict is False


def test_classify_acellular_virus_and_phage() -> None:
    hiv = classify_organism("hiv", 11676)
    phage = classify_organism("Enterobacteria phage lambda", 10710)

    assert hiv.organism_class == OrganismClass.ACELLULAR
    assert phage.organism_class == OrganismClass.ACELLULAR


def test_classify_unicellular_microorganisms() -> None:
    ecoli = classify_organism("Escherichia coli", 562)
    candida = classify_organism("Candida albicans", 5476)

    assert ecoli.organism_class == OrganismClass.UNICELLULAR
    assert candida.organism_class == OrganismClass.UNICELLULAR


def test_alias_lookup_without_taxonomy_id() -> None:
    hiv = classify_organism("HiV", None)
    rice = classify_organism("  rice  ", None)
    monkey = classify_organism("monkey", None)

    assert hiv.organism_class == OrganismClass.ACELLULAR
    assert hiv.source == "organism_name"
    assert rice.organism_class == OrganismClass.MULTICELLULAR
    assert monkey.organism_class == OrganismClass.MULTICELLULAR


def test_conflict_prefers_taxonomy_id_and_sets_flag() -> None:
    result = classify_organism("Escherichia coli", 9606)

    assert result.organism_class == OrganismClass.MULTICELLULAR
    assert result.source == "taxonomy_id"
    assert result.source_conflict is True


def test_handles_strain_names_and_parentheses_normalization() -> None:
    result = classify_organism("Plasmodium falciparum 3D7 (lab strain)", None)

    assert result.organism_class == OrganismClass.UNICELLULAR
    assert result.normalized_organism == "plasmodium falciparum"


def test_invalid_input_unresolved() -> None:
    result = classify_organism("", "invalid")

    assert result.organism_class is None
    assert result.source == "unresolved"
    assert result.reason == "insufficient_or_unrecognized_input"
