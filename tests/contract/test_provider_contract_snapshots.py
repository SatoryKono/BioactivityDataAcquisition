"""Replay-schema tests for provider contract snapshot registries."""

from __future__ import annotations

import pytest
from tests.contract._provider_contract_drift import (
    assert_provider_snapshot_registry_shape,
    load_provider_contract_snapshot,
)

pytestmark = pytest.mark.no_api


@pytest.mark.parametrize(
    ("provider", "expected_probes"),
    [
        (
            "chembl",
            {
                "activity_endpoint_schema",
                "molecule_endpoint_schema",
                "target_endpoint_schema",
            },
        ),
        (
            "semanticscholar",
            {"paper_search_endpoint", "paper_batch_lookup_by_doi"},
        ),
    ],
)
def test_provider_snapshot_registry_shape_replay_lane(
    provider: str, expected_probes: set[str]
) -> None:
    snapshot = load_provider_contract_snapshot(provider)
    assert_provider_snapshot_registry_shape(snapshot)
    assert set(snapshot["probes"]) == expected_probes
