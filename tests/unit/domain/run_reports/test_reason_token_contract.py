"""Unbound reason tokens stay explicitly unknown rather than becoming field reasons."""

from __future__ import annotations

import pytest

from bioetl.domain.run_reports.reason_catalog import (
    UNKNOWN_REASON,
    compose_field_reason_code,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("base", ["", " ", "\t\n"])
def test_empty_reason_cannot_be_made_valid_by_field_suffix(base):
    assert compose_field_reason_code(base, "entity_id") == UNKNOWN_REASON
