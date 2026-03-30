"""Tests for ChEMBL-specific normalization helpers."""

from __future__ import annotations

from bioetl.domain.normalization_chembl import (
    normalize_bao_identifier,
    normalize_chembl_organism_name,
    normalize_qudt_unit,
    normalize_standard_unit,
    normalize_uo_identifier,
)


class TestNormalizeOntologyIdentifiers:
    """Normalization tests for ontology identifiers."""

    def test_normalize_bao_identifier_collapses_separator_and_case(self) -> None:
        assert normalize_bao_identifier("  bao:0000190  ") == "BAO_0000190"

    def test_normalize_uo_identifier_collapses_separator_and_case(self) -> None:
        assert normalize_uo_identifier("uo:0000065") == "UO_0000065"


class TestNormalizeUnits:
    """Normalization tests for ChEMBL unit fields."""

    def test_normalize_standard_unit_uses_shared_alias_rules(self) -> None:
        assert normalize_standard_unit(" nanomolar ") == "nM"
        assert normalize_standard_unit("uM") == "µM"

    def test_normalize_qudt_unit_trims_but_preserves_uri(self) -> None:
        value = " http://www.openphacts.org/units/Nanomolar "
        assert (
            normalize_qudt_unit(value)
            == "http://www.openphacts.org/units/Nanomolar"
        )


class TestNormalizeOrganismName:
    """Normalization tests for target organism display values."""

    def test_normalize_known_scientific_name_to_canonical_display(self) -> None:
        assert (
            normalize_chembl_organism_name("  homo sapiens (Human) ")
            == "Homo sapiens"
        )

    def test_normalize_alias_to_canonical_display(self) -> None:
        assert normalize_chembl_organism_name("e. coli") == "Escherichia coli"

    def test_normalize_nested_parenthetical_annotation(self) -> None:
        assert (
            normalize_chembl_organism_name(
                "Influenza A virus (A/Puerto Rico/8/1934(H1N1))"
            )
            == "Influenza A virus"
        )
