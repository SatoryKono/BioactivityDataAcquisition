"""
Tests for field normalizers.
"""

import pandas as pd
import pytest

from bioetl.domain.transform.normalizers import (
    CUSTOM_FIELD_NORMALIZERS,
    normalize_array,
    normalize_chembl_id,
    normalize_clinical_phase,
    normalize_doi,
    normalize_pcid,
    normalize_pmid,
    normalize_record,
    normalize_uniprot,
)


class TestNormalizeDoi:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("https://doi.org/10.1000/ABC ", "10.1000/abc"),
            ("DOI:10.5555/XYZ", "10.5555/xyz"),
            ("10.1234/foo.bar", "10.1234/foo.bar"),
            (None, None),
            (pd.NA, None),
        ],
    )
    def test_valid_values(self, value, expected):
        assert normalize_doi(value) == expected

    @pytest.mark.parametrize(
        "value",
        [123, {"doi": "10.1/2"}, "not-a-doi"],
    )
    def test_invalid_values(self, value):
        with pytest.raises(ValueError):
            normalize_doi(value)


class TestNormalizeChemblId:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("chembl12", "CHEMBL12"),
            ("12", "CHEMBL12"),
            (" CHEMBL0012 ", "CHEMBL0012"),
            (None, None),
            (pd.NA, None),
        ],
    )
    def test_valid_values(self, value, expected):
        assert normalize_chembl_id(value) == expected

    @pytest.mark.parametrize(
        "value",
        ["CHEMBL12X", "abc", -5],
    )
    def test_invalid_values(self, value):
        with pytest.raises(ValueError):
            normalize_chembl_id(value)


class TestNormalizePmid:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("12345", 12345),
            (12345, 12345),
            (" 67890 ", 67890),
            (None, None),
            (pd.NA, None),
        ],
    )
    def test_valid_values(self, value, expected):
        assert normalize_pmid(value) == expected

    @pytest.mark.parametrize(
        "value",
        ["pmid123", -1, 0, "12a"],
    )
    def test_invalid_values(self, value):
        with pytest.raises(ValueError):
            normalize_pmid(value)


class TestNormalizePcid:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("CID987", 987),
            ("pcid123", 123),
            (" 456 ", 456),
            (None, None),
            (pd.NA, None),
        ],
    )
    def test_valid_values(self, value, expected):
        assert normalize_pcid(value) == expected

    @pytest.mark.parametrize("value", ["CID98X", "cid-1", {"cid": 1}])
    def test_invalid_values(self, value):
        with pytest.raises(ValueError):
            normalize_pcid(value)


class TestNormalizeClinicalPhase:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (0, 0),
            (4, 4),
            (" 2 ", 2),
            (3.0, 3),
            (-1, None),
            (5, None),
            (1.5, None),
            ("", None),
            (None, None),
            (pd.NA, None),
        ],
    )
    def test_valid_values(self, value, expected):
        assert normalize_clinical_phase(value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            "phase2",
            object(),
        ],
    )
    def test_invalid_values(self, value):
        with pytest.raises(ValueError):
            normalize_clinical_phase(value)


class TestNormalizeUniprot:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("p12345", "P12345"),
            ("q9h0h5", "Q9H0H5"),
            ("B7ZC07", "B7ZC07"),
            ("a0a023gpi8", "A0A023GPI8"),
            (None, None),
            (pd.NA, None),
        ],
    )
    def test_valid_values(self, value, expected):
        assert normalize_uniprot(value) == expected

    @pytest.mark.parametrize("value", ["invalid", 123, "Q9H0H5-2"])
    def test_invalid_values(self, value):
        with pytest.raises(ValueError):
            normalize_uniprot(value)


class TestNormalizeArray:
    def test_normalizes_elements_and_types(self):
        result = normalize_array([" 123 ", 456, None], item_normalizer=normalize_pmid)
        assert result == [123, 456]
        assert isinstance(result, list)

    def test_handles_nested_records(self):
        values = [
            {"pmid": "123"},
            {"pmid": 456},
            None,
        ]

        def dict_normalizer(d):
            return normalize_record(d, value_normalizer=normalize_pmid)

        result = normalize_array(values, item_normalizer=dict_normalizer)
        assert result == [{"pmid": 123}, {"pmid": 456}]

    def test_raises_on_invalid_item(self):
        with pytest.raises(ValueError):
            normalize_array(["123", "invalid"], item_normalizer=normalize_pmid)

    def test_accepts_scalar_input(self):
        assert normalize_array("123", item_normalizer=normalize_pmid) == [123]

    def test_returns_empty_on_empty_scalar(self):
        assert normalize_array("", item_normalizer=normalize_pmid) == []

    def test_returns_none_for_empty(self):
        assert normalize_array([], item_normalizer=normalize_pmid) == []


class TestNormalizeRecord:
    def test_normalizes_mapping_values(self):
        record = {"pmid": "123", "extra": None}
        result = normalize_record(record, value_normalizer=normalize_pmid)
        assert result == {"pmid": 123}
        assert isinstance(result, dict)

    def test_returns_none_for_empty_or_missing(self):
        assert normalize_record({}, value_normalizer=normalize_pmid) is None
        assert normalize_record(None, value_normalizer=normalize_pmid) is None

    def test_raises_on_invalid_value(self):
        with pytest.raises(ValueError):
            normalize_record({"pmid": "bad"}, value_normalizer=normalize_pmid)

    def test_raises_on_non_mapping(self):
        with pytest.raises(ValueError):
            normalize_record(["not", "a", "dict"], value_normalizer=normalize_pmid)


class TestCustomFieldNormalizers:
    def test_registry_contains_expected_keys(self):
        expected_keys = {
            "doi",
            "doi_chembl",
            "document_chembl_id",
            "assay_chembl_id",
            "molecule_chembl_id",
            "target_chembl_id",
            "pubmed_id",
            "pmid",
            "pcid",
            "pubchem_cid",
            "uniprot_accession",
            "uniprot_id",
            "accession",
            "max_phase",
        }
        assert expected_keys.issubset(CUSTOM_FIELD_NORMALIZERS.keys())


class TestNormalizeRecordSpecialCases:
    def test_normalize_record_normalizes_accession(self):
        record = {"accession": "p12345", "type": "PROTEIN"}
        result = normalize_record(record)
        assert result == {"accession": "P12345", "type": "PROTEIN"}

    def test_normalize_record_normalizes_xref_id_with_source(self):
        record = {"xref_src": "PubChem", "xref_id": "CID123"}
        result = normalize_record(record)
        assert result == {"xref_src": "PubChem", "xref_id": 123}

    def test_normalize_record_normalizes_xref_id_uniprot(self):
        record = {"xref_src": "UniProt", "xref_id": "p12345"}
        result = normalize_record(record)
        assert result == {"xref_src": "UniProt", "xref_id": "P12345"}

    def test_normalize_record_normalizes_component_synonyms_list(self):
        record = {
            "target_component_synonyms": [" beta ", "alpha", None],
        }
        result = normalize_record(record)
        assert result == {"target_component_synonyms": "alpha|beta"}

    def test_normalize_record_normalizes_component_synonyms_json_string(self):
        record = {
            "target_component_synonyms": '["gamma","Alpha"]',
        }
        result = normalize_record(record)
        assert result == {"target_component_synonyms": "Alpha|gamma"}

    def test_normalize_record_normalizes_component_xrefs(self):
        record = {
            "target_component_xrefs": [
                {"xref_src": "UniProt", "xref_id": "p12345"},
                {"xref_src": "PubChem", "xref_id": "CID42"},
            ]
        }
        result = normalize_record(record)
        assert result == {
            "target_component_xrefs": (
                "xref_id:P12345|xref_src:UniProt|xref_id:42|xref_src:PubChem"
            )
        }
