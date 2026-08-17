"""Unit tests for reproducibility score-card primitives."""

from __future__ import annotations

import pytest

from bioetl.application.services.control_plane.replay.reproducibility_score_cards_types import (
    bounded,
    string_items,
    supported_boundary_block_reason,
)

pytestmark = pytest.mark.unit


def test_reproducibility_scoring_support_bounds_and_normalizes_values() -> None:
    assert bounded(-5) == 0
    assert bounded(7) == 7
    assert bounded(15) == 10

    assert string_items("not-a-list") == ()
    assert string_items(["exact", None, 3]) == ("exact", "3")

    assert (
        supported_boundary_block_reason({"reason": "missing_lineage"})
        == "missing_lineage"
    )
    assert (
        supported_boundary_block_reason({"reason": ""})
        == "blocked_outside_supported_boundary"
    )
    assert supported_boundary_block_reason(None) == "blocked_outside_supported_boundary"
