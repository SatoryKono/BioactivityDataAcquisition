"""Saved evidence cannot invent counts or hide over-accounted removals."""

from __future__ import annotations

import pytest
from bioetl.domain.run_reports.accounting_projections import (
    _prefer_conserving_projection,
    reconcile_saved_layer_counts,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("identity,layers", [(None, {}), ({}, None), ([], [])])
def test_fully_tracked_but_malformed_saved_evidence_does_not_supply_counts(
    identity, layers
):
    result = reconcile_saved_layer_counts(
        {"tracking_coverage": "full", "identity": identity, "layers": layers},
        run_id="run",
        manifest_id="manifest",
        pipeline="pipeline",
        run_types=("pipeline",),
        known_counts={},
    )
    assert result == {}


def test_over_accounted_removals_remain_visible_instead_of_coarse_replacement():
    result = _prefer_conserving_projection(
        records_in=100,
        records_out=95,
        removed_total=20,
        default_in=100,
        default_out=90,
        default_removed=10,
        removed_mapped=20,
    )
    assert result == (100, 95, 20)
    assert result[0] != result[1] + result[2]
