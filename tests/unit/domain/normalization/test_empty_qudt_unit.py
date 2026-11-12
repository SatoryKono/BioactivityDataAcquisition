"""Absent unit tokens do not fabricate ontology identifiers."""

from __future__ import annotations

import pytest
from bioetl.domain.normalization._chembl_units import resolve_qudt_unit_identifier

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("token", ["", " ", "not-a-known-unit"])
def test_unresolved_unit_has_no_qudt_identifier(token):
    assert resolve_qudt_unit_identifier(token) is None
