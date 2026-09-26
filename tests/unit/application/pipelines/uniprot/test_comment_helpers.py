# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Dedicated unit tests for UniProt comment helper functions."""

from __future__ import annotations

import pytest

from bioetl.application.pipelines.uniprot.extractors._comment_helpers import (
    _build_isoform_data,
    _extract_absorption_data,
    _extract_biophys_from_comment,
    _extract_cofactor_entry,
    _extract_kinetic_parameters,
    _extract_km_entry,
    _extract_list_entries,
    _extract_location_value,
    _extract_reaction_data,
    _extract_texts_from_dict,
    _extract_vmax_entry,
    _extract_isoform_id_values,
    _extract_isoform_name_values,
    _extract_isoform_synonym_values,
    _is_comment_of_type,
    _iter_alternative_product_isoforms,
)


@pytest.mark.unit
class TestCommentHelperBasics:
    """Core type/text helper behavior."""

    def test_is_comment_of_type_handles_non_dict_payload(self) -> None:
        assert _is_comment_of_type("COFACTOR", "COFACTOR") is False

    def test_is_comment_of_type_matches_exact_type(self) -> None:
        comment = {"commentType": "COFACTOR"}
        assert _is_comment_of_type(comment, "COFACTOR") is True
        assert _is_comment_of_type(comment, "FUNCTION") is False

    def test_extract_reaction_data_emits_present_fields(self) -> None:
        reaction = {"name": "ATP + H2O = ADP + Pi", "ecNumber": "3.6.1.3"}
        assert _extract_reaction_data(reaction) == {
            "reaction": "ATP + H2O = ADP + Pi",
            "ec_number": "3.6.1.3",
        }

    def test_extract_reaction_data_skips_missing_fields(self) -> None:
        assert _extract_reaction_data({}) == {}

    def test_extract_location_value_handles_missing_or_malformed_input(self) -> None:
        assert (
            _extract_location_value({"location": {"value": "Cytoplasm"}}) == "Cytoplasm"
        )
        assert _extract_location_value({"location": {}}) is None
        assert _extract_location_value({"location": "Cytoplasm"}) is None

    def test_extract_texts_from_dict_handles_malformed_payloads(self) -> None:
        assert _extract_texts_from_dict(None) == []
        assert _extract_texts_from_dict("not-a-dict") == []
        assert _extract_texts_from_dict({"texts": "not-a-list"}) == []
        assert _extract_texts_from_dict(
            {"texts": [{"value": "A"}, {}, {"value": "B"}]}
        ) == [
            "A",
            "B",
        ]

    def test_build_isoform_data_serializes_ids_and_name(self) -> None:
        iso = {
            "isoformIds": ["P12345-1", "P12345-2"],
            "name": {"value": "Canonical"},
        }
        assert _build_isoform_data(iso) == {
            "ids": ["P12345-1", "P12345-2"],
            "name": "Canonical",
        }

    def test_build_isoform_data_returns_empty_when_optional_fields_missing(
        self,
    ) -> None:
        assert _build_isoform_data({"isoformIds": [], "name": {}}) == {}


@pytest.mark.unit
class TestIsoformExtraction:
    """Alternative-products and isoform extraction helpers."""

    def test_extract_isoform_id_values_normalizes_to_strings(self) -> None:
        assert _extract_isoform_id_values({"isoformIds": ["P12345-1", 2, None]}) == [
            "P12345-1",
            "2",
        ]

    def test_extract_isoform_id_values_handles_non_list(self) -> None:
        assert _extract_isoform_id_values({"isoformIds": "P12345-1"}) == []

    def test_extract_isoform_name_values_handles_missing_value(self) -> None:
        assert _extract_isoform_name_values({"name": {"value": "Canonical"}}) == [
            "Canonical"
        ]
        assert _extract_isoform_name_values({"name": {}}) == []
        assert _extract_isoform_name_values({"name": "Canonical"}) == []

    def test_extract_isoform_synonym_values_filters_invalid_entries(self) -> None:
        iso = {
            "synonyms": [
                {"value": "Isoform A"},
                {"value": ""},
                {"raw": "ignored"},
                "invalid",
            ]
        }
        assert _extract_isoform_synonym_values(iso) == ["Isoform A"]

    def test_iter_alternative_product_isoforms_collects_only_dict_isoforms(
        self,
    ) -> None:
        comments = [
            {"commentType": "FUNCTION", "isoforms": [{"name": {"value": "ignored"}}]},
            {
                "commentType": "ALTERNATIVE PRODUCTS",
                "isoforms": [{"name": {"value": "A"}}, "bad", {"name": {"value": "B"}}],
            },
        ]

        isoforms = _iter_alternative_product_isoforms(comments)

        assert isoforms == [{"name": {"value": "A"}}, {"name": {"value": "B"}}]

    def test_iter_alternative_product_isoforms_handles_malformed_payloads(self) -> None:
        assert _iter_alternative_product_isoforms(None) == []
        assert _iter_alternative_product_isoforms([]) == []
        assert (
            _iter_alternative_product_isoforms(
                [{"commentType": "ALTERNATIVE PRODUCTS", "isoforms": "bad"}]
            )
            == []
        )


@pytest.mark.unit
class TestCofactorAndKineticsExtraction:
    """Cofactor and kinetic-parameters helper behavior."""

    def test_extract_cofactor_entry_supports_single_and_multi_note_values(self) -> None:
        one_note = {
            "name": "Mg2+",
            "cofactorCrossReference": {"id": "CHEBI:18420"},
            "note": {"texts": [{"value": "Required for activity"}]},
        }
        many_notes = {
            "name": "Zn2+",
            "note": {
                "texts": [{"value": "Binding site 1"}, {"value": "Binding site 2"}]
            },
        }

        assert _extract_cofactor_entry(one_note) == {
            "name": "Mg2+",
            "chebi_id": "CHEBI:18420",
            "note": "Required for activity",
        }
        assert _extract_cofactor_entry(many_notes) == {
            "name": "Zn2+",
            "note": ["Binding site 1", "Binding site 2"],
        }

    def test_extract_cofactor_entry_handles_missing_fields(self) -> None:
        assert _extract_cofactor_entry({}) == {}

    def test_extract_km_and_vmax_entries_emit_only_present_fields(self) -> None:
        assert _extract_km_entry(
            {"constant": 0.5, "unit": "mM", "substrate": "ATP"}
        ) == {
            "value": 0.5,
            "unit": "mM",
            "substrate": "ATP",
        }
        assert _extract_km_entry({"unit": "mM"}) == {"unit": "mM"}

        assert _extract_vmax_entry(
            {"velocity": 120, "unit": "umol/min/mg", "enzyme": "recombinant"}
        ) == {
            "value": 120,
            "unit": "umol/min/mg",
            "enzyme": "recombinant",
        }
        assert _extract_vmax_entry({"velocity": 25}) == {"value": 25}

    def test_extract_list_entries_handles_none_and_non_dict_items(self) -> None:
        assert _extract_list_entries(None, _extract_km_entry) == []
        assert _extract_list_entries("bad", _extract_km_entry) == []
        assert _extract_list_entries(
            [{"constant": 1}, "bad", {"unit": "mM"}], _extract_km_entry
        ) == [
            {"value": 1},
            {"unit": "mM"},
        ]

    def test_extract_kinetic_parameters_handles_partial_payload(self) -> None:
        kinetics = {
            "michaelisConstants": [{"constant": 0.2, "substrate": "NADH"}],
            "maximumVelocities": [{"velocity": 90}],
            "note": {"texts": [{"value": "Measured at 25C"}]},
        }
        extracted = _extract_kinetic_parameters(kinetics)
        assert extracted == {
            "km": [{"value": 0.2, "substrate": "NADH"}],
            "vmax": [{"value": 90}],
            "note": ["Measured at 25C"],
        }

    def test_extract_kinetic_parameters_returns_empty_for_empty_structure(self) -> None:
        assert _extract_kinetic_parameters({}) == {}
        assert _extract_kinetic_parameters({"michaelisConstants": []}) == {}


@pytest.mark.unit
class TestAbsorptionAndBiophysExtraction:
    """Absorption and biophysicochemical extraction helpers."""

    def test_extract_absorption_data_handles_notes_and_missing_max(self) -> None:
        assert _extract_absorption_data(
            {"max": 330, "note": {"texts": [{"value": "Measured in UV range"}]}}
        ) == {"max": 330, "note": ["Measured in UV range"]}
        assert _extract_absorption_data({"note": {"texts": []}}) == {}

    def test_extract_biophys_from_comment_extracts_all_supported_sections(self) -> None:
        comment = {
            "phDependence": {"texts": [{"value": "pH optimum 7.5"}]},
            "temperatureDependence": {"texts": [{"value": "Stable up to 40C"}]},
            "redoxPotential": {"texts": [{"value": "-320mV"}]},
            "kineticParameters": {
                "michaelisConstants": [{"constant": 0.3, "unit": "mM"}],
                "maximumVelocities": [{"velocity": 100, "unit": "U/mg"}],
            },
            "absorption": {
                "max": 340,
                "note": {"texts": [{"value": "Peak in near UV"}]},
            },
        }

        extracted = _extract_biophys_from_comment(comment)
        assert extracted["ph_dependence"] == ["pH optimum 7.5"]
        assert extracted["temperature_dependence"] == ["Stable up to 40C"]
        assert extracted["redox_potential"] == ["-320mV"]
        assert extracted["kinetic_parameters"]["km"] == [{"value": 0.3, "unit": "mM"}]
        assert extracted["kinetic_parameters"]["vmax"] == [
            {"value": 100, "unit": "U/mg"}
        ]
        assert extracted["absorption"] == {"max": 340, "note": ["Peak in near UV"]}

    def test_extract_biophys_from_comment_defensive_for_malformed_nested_payloads(
        self,
    ) -> None:
        comment = {
            "phDependence": None,
            "temperatureDependence": {"texts": "bad"},
            "redoxPotential": {"texts": [{"value": "ok"}]},
            "kineticParameters": "not-a-dict",
            "absorption": ["not-a-dict"],
        }

        extracted = _extract_biophys_from_comment(comment)
        assert extracted == {"redox_potential": ["ok"]}
