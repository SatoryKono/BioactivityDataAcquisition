"""Tests for ChEMBL-specific normalization helpers."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.chembl import (
    normalize_bao_identifier,
    normalize_bao_label,
    normalize_chembl_organism_name,
    normalize_qudt_unit,
    normalize_standard_unit,
    normalize_uo_identifier,
)

LEGACY_QUDT_UNIT_URI = "http" + "://www.openphacts.org/units/Nanomolar"


class TestNormalizeOntologyIdentifiers:
    """Normalization tests for ontology identifiers."""

    def test_normalize_bao_identifier_collapses_separator_and_case(self) -> None:
        assert normalize_bao_identifier("  bao:0000190  ") == "BAO_0000190"

    def test_normalize_bao_identifier_preserves_canonical_form(self) -> None:
        assert normalize_bao_identifier("BAO_0000218") == "BAO_0000218"

    def test_normalize_bao_identifier_returns_none_for_blank(self) -> None:
        assert normalize_bao_identifier("   ") is None

    def test_normalize_bao_label_prefers_canonical_label_from_identifier(self) -> None:
        assert (
            normalize_bao_label(
                " Single Protein Format ",
                bao_identifier="bao:0000357",
            )
            == "single protein format"
        )

    def test_normalize_bao_label_can_derive_label_from_identifier_only(self) -> None:
        assert normalize_bao_label(None, bao_identifier="BAO_0000219") == (
            "cell-based format"
        )

    def test_normalize_bao_label_trims_and_lowercases_unknown_label(self) -> None:
        assert normalize_bao_label("  Assay Format  ") == "assay format"

    def test_normalize_bao_label_returns_none_for_blank(self) -> None:
        assert normalize_bao_label("\t") is None

    def test_normalize_uo_identifier_collapses_separator_and_case(self) -> None:
        assert normalize_uo_identifier("uo:0000065") == "UO_0000065"

    def test_normalize_uo_identifier_preserves_canonical_form(self) -> None:
        assert normalize_uo_identifier("UO_0000065") == "UO_0000065"

    def test_normalize_uo_identifier_returns_none_for_blank(self) -> None:
        assert normalize_uo_identifier("") is None


class TestNormalizeUnits:
    """Normalization tests for ChEMBL unit fields."""

    def test_normalize_standard_unit_uses_shared_alias_rules(self) -> None:
        assert normalize_standard_unit(" nanomolar ") == "nM"
        assert normalize_standard_unit("uM") == "µM"

    def test_normalize_qudt_unit_trims_but_preserves_uri(self) -> None:
        value = f" {LEGACY_QUDT_UNIT_URI} "
        assert normalize_qudt_unit(value) == LEGACY_QUDT_UNIT_URI

    def test_normalize_standard_unit_preserves_unknown_trimmed_value(self) -> None:
        assert normalize_standard_unit(" ratio ") == "ratio"

    def test_normalize_standard_unit_returns_none_for_blank(self) -> None:
        assert normalize_standard_unit("  ") is None

    def test_normalize_qudt_unit_returns_none_for_blank(self) -> None:
        assert normalize_qudt_unit("\t") is None


class TestNormalizeOrganismName:
    """Normalization tests for target organism display values."""

    def test_normalize_known_scientific_name_to_canonical_display(self) -> None:
        assert (
            normalize_chembl_organism_name("  homo sapiens (Human) ") == "Homo sapiens"
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

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("Homo\n        sapiens", "Homo sapiens"),
            (
                "Candida albicans (strain SC5314 / ATCC MYA-2876) (Yeast)",
                "Candida albicans",
            ),
            (
                "Influenza A virus (strain A/Udorn/1972 H3N2)",
                "Influenza A virus",
            ),
            (
                "Mycobacterium tuberculosis (strain ATCC 25618 / H37Rv)",
                "Mycobacterium tuberculosis",
            ),
        ],
    )
    def test_normalize_historical_vcr_variants_to_canonical_display(
        self, raw_value: str, expected: str
    ) -> None:
        """Historical VCR lexical variants should collapse to canonical display."""
        assert normalize_chembl_organism_name(raw_value) == expected
