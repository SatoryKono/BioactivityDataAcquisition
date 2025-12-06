import pandas as pd
import pytest

from bioetl.domain.transform.normalizers import (
    BAO_ID_REGEX,
    CHEMBL_ID_REGEX,
    DOI_REGEX,
    UNIPROT_ID_REGEX,
    normalize_array,
    normalize_bao_id,
    normalize_bao_label,
    normalize_chembl_id,
    normalize_doi,
    normalize_pcid,
    normalize_pmid,
    normalize_record,
    normalize_uniprot,
)


class TestCustomTypes:
    """Tests for custom type normalizers and regex constants."""

    def test_normalize_doi(self):
        # Valid cases
        assert normalize_doi("10.1000/182") == "10.1000/182"
        assert normalize_doi("DOI:10.1000/182") == "10.1000/182"
        assert normalize_doi("doi:10.1000/182") == "10.1000/182"
        assert normalize_doi("https://doi.org/10.1000/182") == "10.1000/182"
        assert normalize_doi("http://dx.doi.org/10.1000/182") == "10.1000/182"
        assert normalize_doi("  10.1000/182  ") == "10.1000/182"

        # Case insensitive for prefix, lowercase body?
        # Implementation lowercases entire string.
        assert normalize_doi("DOI:10.1000/ABC") == "10.1000/abc"

        # Invalid cases
        with pytest.raises(ValueError, match="Неверный формат DOI"):
            normalize_doi("INVALID")

        with pytest.raises(ValueError, match="Неверный формат DOI"):
            normalize_doi("9.1234/567")  # wrong prefix

        assert normalize_doi(None) is None
        assert normalize_doi(pd.NA) is None

    def test_normalize_chembl_id(self):
        # Valid
        assert normalize_chembl_id("CHEMBL12345") == "CHEMBL12345"
        assert normalize_chembl_id("chembl12345") == "CHEMBL12345"
        assert normalize_chembl_id("Chembl123") == "CHEMBL123"
        assert normalize_chembl_id("12345") == "CHEMBL12345"

        # Invalid
        with pytest.raises(ValueError, match="Неверный ChEMBL ID"):
            normalize_chembl_id("CHEMBL")  # Missing digits

        with pytest.raises(ValueError, match="Неверный ChEMBL ID"):
            normalize_chembl_id("CHEMBL_123")  # Underscore

        assert normalize_chembl_id(None) is None

    def test_normalize_pmid(self):
        # Valid
        assert normalize_pmid(12345) == 12345
        assert normalize_pmid("12345") == 12345
        assert normalize_pmid(123.0) == 123
        assert normalize_pmid(" 12345 ") == 12345

        # Invalid
        with pytest.raises(ValueError, match="положительным числом"):
            normalize_pmid(-1)

        with pytest.raises(ValueError, match="положительным числом"):
            normalize_pmid(0)

        with pytest.raises(ValueError, match="нецифровые символы"):
            normalize_pmid("12A45")

        with pytest.raises(ValueError, match="нецифровые символы"):
            normalize_pmid("PMC123")

        assert normalize_pmid(None) is None

    def test_normalize_pcid(self):
        # Valid
        assert normalize_pcid(2244) == 2244
        assert normalize_pcid("2244") == 2244
        assert normalize_pcid("CID2244") == 2244
        assert normalize_pcid("PCID2244") == 2244

        # Invalid
        with pytest.raises(ValueError, match="Неверный PubChem CID"):
            normalize_pcid("ABC")

        with pytest.raises(ValueError, match="положительным числом"):
            normalize_pcid(0)

        assert normalize_pcid(None) is None

    def test_normalize_uniprot(self):
        # Valid
        assert normalize_uniprot("P12345") == "P12345"
        assert normalize_uniprot("p12345") == "P12345"
        assert normalize_uniprot("A0A0P7VRU5") == "A0A0P7VRU5"  # 10 chars

        # Invalid
        with pytest.raises(ValueError, match="Неверный UniProt ID"):
            normalize_uniprot("P1234")  # too short

        with pytest.raises(ValueError, match="Неверный UniProt ID"):
            normalize_uniprot("P1234567")  # wrong length

        with pytest.raises(ValueError, match="Неверный UniProt ID"):
            normalize_uniprot("123456")  # all digits (regex requires letter start)

        assert normalize_uniprot(None) is None

    def test_normalize_bao_id(self):
        # Valid
        assert normalize_bao_id("BAO_0000190") == "BAO_0000190"
        assert normalize_bao_id("bao_0000190") == "BAO_0000190"

        # Invalid
        with pytest.raises(ValueError, match="Неверный BAO ID"):
            normalize_bao_id("BAO123")  # Missing underscore

        with pytest.raises(ValueError, match="Неверный BAO ID"):
            normalize_bao_id("123")

        assert normalize_bao_id(None) is None

    def test_normalize_bao_label(self):
        # Valid
        assert normalize_bao_label(" single protein format ") == "single protein format"
        assert normalize_bao_label("IC50") == "IC50"

        # Empty
        assert normalize_bao_label("") is None
        assert normalize_bao_label("   ") is None
        assert normalize_bao_label(None) is None

        # Numeric handling
        assert normalize_bao_label(123) == "123"

    def test_normalize_array(self):
        # List input
        assert normalize_array(["a", "b"]) == ["a", "b"]
        assert normalize_array([1, 2]) == ["1", "2"]  # auto stringify

        # Single input
        assert normalize_array("foo") == ["foo"]

        # String representation
        assert normalize_array('["a", "b"]') == ["a", "b"]
        # Heuristic split?
        # The implementation supports basic JSON check.

        # Empty
        assert normalize_array([]) == []
        # normalize_array now returns [] for None (changed to always return list)
        assert normalize_array(None) == []

        # With item normalizer
        assert normalize_array(
            ["P12345", "Q12345"], item_normalizer=normalize_uniprot
        ) == ["P12345", "Q12345"]

        with pytest.raises(ValueError, match="Ошибка нормализации"):
            normalize_array(["INVALID"], item_normalizer=normalize_uniprot)

    def test_normalize_record(self):
        # Dict input
        assert normalize_record({"a": 1}) == {"a": 1}

        # String JSON
        assert normalize_record('{"a": 1}') == {"a": 1}

        # Invalid
        with pytest.raises(ValueError, match="Ожидался словарь"):
            normalize_record(["list"])

        with pytest.raises(ValueError, match="Некорректный JSON"):
            normalize_record('{"a":}')

        # With value normalizer
        # NOTE: normalizer applies to VALUES, not keys.
        data = {"id": "P12345"}
        assert normalize_record(data, value_normalizer=normalize_uniprot) == {
            "id": "P12345"
        }

        with pytest.raises(ValueError, match="Некорректное значение"):
            normalize_record({"id": "INVALID"}, value_normalizer=normalize_uniprot)

    def test_regex_patterns(self):
        assert DOI_REGEX.match("10.1000/abc")
        assert not DOI_REGEX.match("9.1000/abc")

        assert CHEMBL_ID_REGEX.match("CHEMBL123")
        assert not CHEMBL_ID_REGEX.match("123")

        assert UNIPROT_ID_REGEX.match("P12345")
        assert not UNIPROT_ID_REGEX.match("P1234")

        assert BAO_ID_REGEX.match("BAO_0000190")
        assert not BAO_ID_REGEX.match("BAO123")
