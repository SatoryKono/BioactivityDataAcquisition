"""Operator aliases for control-plane reason codes."""

from __future__ import annotations

import pytest

from bioetl.application.observability.reason_aliases import (
    display_reason,
    display_reasons_text,
)

pytestmark = pytest.mark.unit


def test_display_reason_maps_known_codes() -> None:
    assert display_reason("archive_evidence_not_recorded") == "Archive missing"
    assert display_reason("lineage_closure_gap") == "Lineage closure gap"
    assert display_reason("unknown_code") == "unknown_code"


def test_display_reasons_text_maps_each_line() -> None:
    raw = "archive_evidence_not_recorded\nlineage_closure_gap"
    assert display_reasons_text(raw) == "Archive missing\nLineage closure gap"


def test_trust_gap_reasons_have_operator_labels():
    assert (
        display_reasons_text(
            "lineage_fragments_missing\nlineage_identity_not_observable"
        )
        == "Lineage fragments missing\nLineage identity not observable"
    )
