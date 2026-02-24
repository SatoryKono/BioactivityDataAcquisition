"""Tests for assay organism classification."""

from __future__ import annotations

import pytest

from bioetl.domain.mapping.organism_classification import (
    OrganismClass,
    classify_organism,
    normalize_organism_name,
)


class TestNormalizeOrganismName:
    def test_none(self) -> None:
        assert normalize_organism_name(None) is None

    def test_trim_lower_and_parentheses_removal(self) -> None:
        assert normalize_organism_name("  Homo sapiens (Human)  ") == "homo sapiens"

    def test_empty_after_normalization(self) -> None:
        assert normalize_organism_name("   ") is None


class TestTaxonomyPriority:
    @pytest.mark.parametrize(
        ("taxonomy_id", "expected_class"),
        [
            (11676, OrganismClass.ACELLULAR),
            (10710, OrganismClass.ACELLULAR),
            (562, OrganismClass.UNICELLULAR),
            (1280, OrganismClass.UNICELLULAR),
            (9606, OrganismClass.MULTICELLULAR),
            (10116, OrganismClass.MULTICELLULAR),
            (3847, OrganismClass.MULTICELLULAR),
        ],
    )
    def test_classification_by_taxonomy_id(
        self, taxonomy_id: int, expected_class: OrganismClass
    ) -> None:
        result = classify_organism("random", taxonomy_id)
        assert result.organism_class == expected_class
        assert result.source == "taxonomy_id"

    def test_taxonomy_id_wins_on_conflict(self) -> None:
        result = classify_organism("Escherichia coli", 9606)
        assert result.organism_class == OrganismClass.MULTICELLULAR
        assert result.source == "taxonomy_id"
        assert result.source_conflict is True

    def test_unmapped_valid_taxonomy_id_is_unresolved(self) -> None:
        result = classify_organism("Homo sapiens", 999999999)
        assert result.organism_class is None
        assert result.source == "unresolved"
        assert result.reason == "taxonomy_id_not_mapped"


class TestOrganismNameClassification:
    @pytest.mark.parametrize(
        ("organism_name", "expected_class"),
        [
            ("Human immunodeficiency virus 1", OrganismClass.ACELLULAR),
            ("Influenza A virus (A/Puerto Rico/8/1934)", OrganismClass.ACELLULAR),
            ("Enterobacteria phage lambda", OrganismClass.ACELLULAR),
            ("Escherichia coli", OrganismClass.UNICELLULAR),
            ("Staphylococcus aureus", OrganismClass.UNICELLULAR),
            ("Candida albicans", OrganismClass.UNICELLULAR),
            ("Plasmodium falciparum 3D7", OrganismClass.UNICELLULAR),
            ("Homo sapiens", OrganismClass.MULTICELLULAR),
            ("Rattus norvegicus", OrganismClass.MULTICELLULAR),
            ("Glycine max", OrganismClass.MULTICELLULAR),
            ("Streptococcus pneumoniae TIGR4", OrganismClass.UNICELLULAR),
        ],
    )
    def test_classification_by_name(
        self, organism_name: str, expected_class: OrganismClass
    ) -> None:
        result = classify_organism(organism_name, None)
        assert result.organism_class == expected_class
        assert result.source == "organism_name"


class TestAliases:
    @pytest.mark.parametrize(
        ("organism_name", "taxonomy_id", "expected_class", "expected_source"),
        [
            ("hiv", None, OrganismClass.ACELLULAR, "organism_name"),
            ("hiv", 11676, OrganismClass.ACELLULAR, "taxonomy_id"),
            ("rice", None, OrganismClass.MULTICELLULAR, "organism_name"),
            ("eel", 8005, OrganismClass.MULTICELLULAR, "taxonomy_id"),
            ("monkey", 9534, OrganismClass.MULTICELLULAR, "taxonomy_id"),
        ],
    )
    def test_aliases(
        self,
        organism_name: str,
        taxonomy_id: int | None,
        expected_class: OrganismClass,
        expected_source: str,
    ) -> None:
        result = classify_organism(organism_name, taxonomy_id)
        assert result.organism_class == expected_class
        assert result.source == expected_source


class TestInvalidInput:
    @pytest.mark.parametrize("taxonomy_id", [None, "", "abc", "-1", -1, 0])
    def test_invalid_taxonomy_inputs(self, taxonomy_id: int | str | None) -> None:
        result = classify_organism("unknown organism", taxonomy_id)
        assert result.organism_class is None
        assert result.source == "unresolved"

    def test_empty_inputs(self) -> None:
        result = classify_organism(None, None)
        assert result.organism_class is None
        assert result.normalized_organism is None
        assert result.source == "unresolved"
