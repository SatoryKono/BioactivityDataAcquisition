"""Reject nonbinary source values and preserve CALOHA identifier aliases."""

import pytest

from bioetl.domain.normalization.rules import normalize_boolean, normalize_binary_flag
from bioetl.domain.normalization.identifiers import normalize_ontology_id

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("value", ["", "  ", 2, -1, 2.5, float("nan"), None, []])
def test_nonbinary_values_are_not_silently_coerced(value):
    assert normalize_boolean(value) is None
    assert normalize_binary_flag(value) is None


@pytest.mark.parametrize("value", ["CALOHA:TS-0001", "CALOHA_TS-0001", "TS-TS-0001"])
def test_caloha_aliases_do_not_duplicate_the_canonical_prefix(value):
    assert normalize_ontology_id(value) == "TS-0001"
