"""Application URI normalization rejects foreign authorities and preserves unit semantics."""

import pytest

from bioetl.application.normalization import _chembl_units as subject

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "uri,expected",
    [
        ("https://qudt.org/vocab/unit/NanoMOL-PER-L", "NanoMOL-PER-L"),
        (" HTTP://user@QUDT.ORG:80/vocab/unit/GM;version=1?x=/foreign#fragment ", "GM"),
        ("https://qudt.org/vocab/unit/", ""),
        ("https://foreign.invalid/vocab/unit/GM", None),
        ("ftp://qudt.org/vocab/unit/GM", None),
        ("qudt.org/vocab/unit/GM", None),
        ("https://qudt.org?ref=/vocab/unit/GM", None),
        ("https://qudt.org/other/GM", None),
    ],
)
def test_qudt_uri_authority_and_matrix_parameter_contract(uri, expected):
    assert subject._qudt_identifier_from_uri(uri) == expected


@pytest.mark.parametrize(
    "uri,expected",
    [
        ("https://www.openphacts.org/units/nanomolar", "NanoMOL-PER-L"),
        ("http://WWW.OPENPHACTS.ORG/UNITS/NANOMOLAR;v=1?q=x", "NanoMOL-PER-L"),
        ("https://www.openphacts.org/units/micromolar", None),
        ("https://foreign.invalid/units/nanomolar", None),
        ("/units/nanomolar", None),
    ],
)
def test_legacy_unit_only_accepts_the_documented_nanomolar_uri(uri, expected):
    assert subject._legacy_qudt_identifier_from_uri(uri) == expected
