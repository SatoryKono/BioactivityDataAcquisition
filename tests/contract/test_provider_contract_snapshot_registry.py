"""Local registry checks for provider-facing contract snapshots."""

from __future__ import annotations

import pytest

from tests.contract._provider_contract_drift import (
    assert_provider_snapshot_registry_shape,
    load_provider_contract_snapshot,
)

pytestmark = pytest.mark.no_api


@pytest.mark.parametrize("provider", ["crossref", "openalex"])
def test_provider_snapshot_registry_shape(provider: str) -> None:
    snapshot = load_provider_contract_snapshot(provider)
    assert_provider_snapshot_registry_shape(snapshot)
    assert snapshot["provider"] == provider
