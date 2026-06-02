"""Tests for organism cellularity classification."""

from __future__ import annotations

import pytest

from bioetl.domain.mapping.organism_classification import (
    OrganismClassificationResult,
    classify_organism,
    normalize_organism_name,
)
from bioetl.domain.types import CellularityType


pytestmark = pytest.mark.unit


class TestNormalizeOrganismName:
    """Tests for organism name normalization."""

    def test_organism_name__none_returns_none__d06e6e68(self) -> None:
        assert normalize_organism_name(None) is None

    def test_organism_name__string_returns_none__f8d002b1(self) -> None:
        assert normalize_organism_name("") is None
        assert normalize_organism_name("   ") is None

    def test_lowercases_and_strips(self) -> None:
        assert normalize_organism_name("  Homo Sapiens  ") == "homo sapiens"

    def test_removes_parenthetical_annotations(self) -> None:
        assert normalize_organism_name("Homo sapiens (Human)") == "homo sapiens"

    def test_removes_nested_parentheses(self) -> None:
        result = normalize_organism_name(
            "Influenza A virus (A/Puerto Rico/8/1934(H1N1))"
        )
        assert result == "influenza a virus"

    def test_collapses_whitespace(self) -> None:
        assert normalize_organism_name("Escherichia   coli") == "escherichia coli"

    def test_resolves_aliases(self) -> None:
        assert normalize_organism_name("hiv") == "human immunodeficiency virus 1"
        assert normalize_organism_name("rice") == "oryza sativa japonica group"
        assert normalize_organism_name("eel") == "electrophorus electricus"
        assert normalize_organism_name("monkey") == "chlorocebus aethiops"


class TestClassifyByTaxonomyId:
    """Taxonomy ID is the primary classification source."""

    @pytest.mark.parametrize(
        ("taxonomy_id", "expected"),
        [
            # Acellular
            (11676, CellularityType.ACELLULAR),  # HIV-1
            (10710, CellularityType.ACELLULAR),  # Phage lambda
            (211044, CellularityType.ACELLULAR),  # Influenza A
            (694009, CellularityType.ACELLULAR),  # SARS-CoV
            (10665, CellularityType.ACELLULAR),  # Bacteriophage T4
            # Unicellular — bacteria
            (562, CellularityType.UNICELLULAR),  # E. coli
            (1280, CellularityType.UNICELLULAR),  # S. aureus
            (1773, CellularityType.UNICELLULAR),  # M. tuberculosis
            (1313, CellularityType.UNICELLULAR),  # S. pneumoniae
            # Unicellular — archaea
            (2210, CellularityType.UNICELLULAR),  # Methanosarcina
            (187420, CellularityType.UNICELLULAR),  # Methanothermobacter
            # Unicellular — protists/yeasts
            (5476, CellularityType.UNICELLULAR),  # Candida albicans (yeast)
            (5833, CellularityType.UNICELLULAR),  # P. falciparum
            (5888, CellularityType.UNICELLULAR),  # Paramecium
            (870730, CellularityType.UNICELLULAR),  # Ogataea (yeast)
            (5691, CellularityType.UNICELLULAR),  # T. brucei
            # Multicellular — animals
            (9606, CellularityType.MULTICELLULAR),  # Homo sapiens
            (10090, CellularityType.MULTICELLULAR),  # Mus musculus
            (10116, CellularityType.MULTICELLULAR),  # Rattus norvegicus
            (8005, CellularityType.MULTICELLULAR),  # Eel
            (9534, CellularityType.MULTICELLULAR),  # Monkey
            (7227, CellularityType.MULTICELLULAR),  # Drosophila
            # Multicellular — plants
            (3847, CellularityType.MULTICELLULAR),  # Glycine max
            (39947, CellularityType.MULTICELLULAR),  # Oryza sativa
            (4577, CellularityType.MULTICELLULAR),  # Zea mays
            # Multicellular — filamentous fungi
            (5061, CellularityType.MULTICELLULAR),  # Aspergillus niger
            (64495, CellularityType.MULTICELLULAR),  # Rhizopus arrhizus
        ],
    )
    def test_known_taxonomy_ids(
        self, taxonomy_id: int, expected: CellularityType
    ) -> None:
        result = classify_organism("any organism", taxonomy_id)
        assert result.organism_class == expected
        assert result.source == "taxonomy_id"
        assert result.taxonomy_id == taxonomy_id

    def test_taxonomy_id_as_string(self) -> None:
        result = classify_organism("Homo sapiens", "9606")
        assert result.organism_class == CellularityType.MULTICELLULAR
        assert result.taxonomy_id == 9606

    def test_unmapped_valid_taxonomy_id_is_unresolved(self) -> None:
        result = classify_organism("some organism", 999999)
        assert result.organism_class is None
        assert result.source == "unresolved"
        assert result.taxonomy_id == 999999
        assert result.reason is not None
        assert "not mapped" in result.reason

    def test_unmapped_valid_taxonomy_id_falls_back_to_resolved_name(self) -> None:
        result = classify_organism("Influenza A virus", 11320)
        assert result.organism_class == CellularityType.ACELLULAR
        assert result.source == "organism_name"
        assert result.taxonomy_id == 11320
        assert result.reason is not None
        assert "fell back to organism name" in result.reason


class TestClassifyByOrganismName:
    """Organism name is the fallback classification source."""

    @pytest.mark.parametrize(
        ("organism", "expected"),
        [
            ("Homo sapiens", CellularityType.MULTICELLULAR),
            ("Rattus norvegicus", CellularityType.MULTICELLULAR),
            ("Glycine max", CellularityType.MULTICELLULAR),
            ("Drosophila melanogaster", CellularityType.MULTICELLULAR),
            ("Aspergillus niger", CellularityType.MULTICELLULAR),
            ("Escherichia coli", CellularityType.UNICELLULAR),
            ("Staphylococcus aureus", CellularityType.UNICELLULAR),
            ("Candida albicans", CellularityType.UNICELLULAR),
            ("Plasmodium falciparum", CellularityType.UNICELLULAR),
            ("Trypanosoma brucei", CellularityType.UNICELLULAR),
            ("Human immunodeficiency virus 1", CellularityType.ACELLULAR),
            ("Influenza A virus", CellularityType.ACELLULAR),
            ("Enterobacteria phage lambda", CellularityType.ACELLULAR),
        ],
    )
    def test_direct_name_match(self, organism: str, expected: CellularityType) -> None:
        result = classify_organism(organism, None)
        assert result.organism_class == expected
        assert result.source == "organism_name"

    def test_strain_prefix_matching(self) -> None:
        result = classify_organism("Plasmodium falciparum 3D7", None)
        assert result.organism_class == CellularityType.UNICELLULAR
        assert result.source == "organism_name"

    def test_strain_with_parentheses(self) -> None:
        result = classify_organism("Streptococcus pneumoniae (TIGR4)", None)
        assert result.organism_class == CellularityType.UNICELLULAR
        assert result.normalized_organism == "streptococcus pneumoniae"


class TestAliases:
    """Common name aliases resolve correctly."""

    @pytest.mark.parametrize(
        ("alias", "expected_class", "expected_source"),
        [
            ("hiv", CellularityType.ACELLULAR, "organism_name"),
            ("rice", CellularityType.MULTICELLULAR, "organism_name"),
            ("eel", CellularityType.MULTICELLULAR, "organism_name"),
            ("monkey", CellularityType.MULTICELLULAR, "organism_name"),
        ],
    )
    def test_alias_without_taxonomy(
        self,
        alias: str,
        expected_class: CellularityType,
        expected_source: str,
    ) -> None:
        result = classify_organism(alias, None)
        assert result.organism_class == expected_class
        assert result.source == expected_source

    def test_alias_with_taxonomy_id_prefers_taxonomy(self) -> None:
        result = classify_organism("hiv", 11676)
        assert result.organism_class == CellularityType.ACELLULAR
        assert result.source == "taxonomy_id"
        assert result.source_conflict is False

    def test_eel_with_taxonomy_id(self) -> None:
        result = classify_organism("eel", 8005)
        assert result.organism_class == CellularityType.MULTICELLULAR
        assert result.source == "taxonomy_id"


class TestKeywordHeuristics:
    """Keyword-based fallback for unknown organisms."""

    @pytest.mark.parametrize(
        ("organism", "expected"),
        [
            ("some unknown virus strain", CellularityType.ACELLULAR),
            ("novel bacteriophage X", CellularityType.ACELLULAR),
            ("unknown bacterium sp.", CellularityType.UNICELLULAR),
            ("novel bacillus species", CellularityType.UNICELLULAR),
        ],
    )
    def test_keyword_heuristics(self, organism: str, expected: CellularityType) -> None:
        result = classify_organism(organism, None)
        assert result.organism_class == expected
        assert result.source == "organism_name"


class TestGenusFallback:
    """Genus-level fallback covers organisms absent from the species map."""

    @pytest.mark.parametrize(
        ("organism", "expected"),
        [
            ("Cavia porcellus", CellularityType.MULTICELLULAR),
            ("Oryctolagus cuniculus", CellularityType.MULTICELLULAR),
            ("Canis lupus familiaris", CellularityType.MULTICELLULAR),
            ("Klebsiella pneumoniae", CellularityType.UNICELLULAR),
            ("Schistosoma mansoni", CellularityType.MULTICELLULAR),
            ("Arabidopsis thaliana", CellularityType.MULTICELLULAR),
            ("Chlamydomonas reinhardtii", CellularityType.UNICELLULAR),
            ("Trichophyton", CellularityType.MULTICELLULAR),
        ],
    )
    def test_genus_level_fallback(
        self, organism: str, expected: CellularityType
    ) -> None:
        result = classify_organism(organism, None)
        assert result.organism_class == expected
        assert result.source == "organism_name"


class TestSourceConflict:
    """taxonomy_id wins when organism name disagrees."""

    def test_conflict_detected_and_taxonomy_wins(self) -> None:
        # E. coli name (unicellular) + human taxonomy_id (multicellular)
        result = classify_organism("Escherichia coli", 9606)
        assert result.organism_class == CellularityType.MULTICELLULAR
        assert result.source == "taxonomy_id"
        assert result.source_conflict is True
        assert result.reason is not None

    def test_no_conflict_when_both_agree(self) -> None:
        result = classify_organism("Homo sapiens", 9606)
        assert result.organism_class == CellularityType.MULTICELLULAR
        assert result.source_conflict is False
        assert result.reason is None


class TestEdgeCases:
    """Invalid, empty, and edge-case inputs."""

    @pytest.mark.parametrize(
        ("organism", "taxonomy_id"),
        [
            (None, None),
            ("", None),
            ("   ", None),
            (None, "not-an-int"),
            ("", ""),
        ],
    )
    def test_empty_or_invalid_inputs_are_unresolved(
        self,
        organism: str | None,
        taxonomy_id: str | int | None,
    ) -> None:
        result = classify_organism(organism, taxonomy_id)
        assert result.organism_class is None
        assert result.source == "unresolved"

    def test_unknown_organism_name_is_unresolved(self) -> None:
        result = classify_organism("completely unknown organism xyz", None)
        assert result.organism_class is None
        assert result.source == "unresolved"
        assert result.reason is not None

    def test_negative_taxonomy_id_treated_as_none(self) -> None:
        result = classify_organism("Homo sapiens", -1)
        assert result.organism_class == CellularityType.MULTICELLULAR
        assert result.source == "organism_name"
        assert result.taxonomy_id is None

    def test_zero_taxonomy_id_treated_as_none(self) -> None:
        result = classify_organism(None, 0)
        assert result.organism_class is None
        assert result.source == "unresolved"


class TestDifferentiatedFungi:
    """Yeasts are unicellular, filamentous fungi are multicellular."""

    def test_candida_is_unicellular(self) -> None:
        result = classify_organism("Candida albicans", 5476)
        assert result.organism_class == CellularityType.UNICELLULAR

    def test_ogataea_yeast_is_unicellular(self) -> None:
        result = classify_organism("Ogataea angusta", 870730)
        assert result.organism_class == CellularityType.UNICELLULAR

    def test_aspergillus_is_multicellular(self) -> None:
        result = classify_organism("Aspergillus niger", 5061)
        assert result.organism_class == CellularityType.MULTICELLULAR

    def test_rhizopus_is_multicellular(self) -> None:
        result = classify_organism("Rhizopus arrhizus", 64495)
        assert result.organism_class == CellularityType.MULTICELLULAR


class TestResultStructure:
    """OrganismClassificationResult has correct fields."""

    def test_result_is_frozen(self) -> None:
        result = classify_organism("Homo sapiens", 9606)
        with pytest.raises(AttributeError):
            result.organism_class = CellularityType.ACELLULAR  # type: ignore[misc]

    def test_result_fields_populated(self) -> None:
        result = classify_organism("Homo sapiens", 9606)
        assert isinstance(result, OrganismClassificationResult)
        assert result.organism_class == CellularityType.MULTICELLULAR
        assert result.normalized_organism == "homo sapiens"
        assert result.taxonomy_id == 9606
        assert result.source == "taxonomy_id"
        assert result.source_conflict is False
