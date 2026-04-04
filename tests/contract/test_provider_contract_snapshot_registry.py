"""Local registry checks for provider-facing contract snapshots."""

from __future__ import annotations

import pytest

from tests.contract._provider_contract_drift import (
    _resolve_path,
    assert_provider_snapshot_registry_shape,
    load_provider_contract_snapshot,
)

pytestmark = pytest.mark.no_api


@pytest.mark.parametrize(
    "provider",
    [
        "chembl",
        "crossref",
        "openalex",
        "pubchem",
        "pubmed",
        "semanticscholar",
        "uniprot",
    ],
)
def test_provider_snapshot_registry_shape(provider: str) -> None:
    snapshot = load_provider_contract_snapshot(provider)
    assert_provider_snapshot_registry_shape(snapshot)
    assert snapshot["provider"] == provider


def test_root_list_snapshot_paths_are_supported() -> None:
    payload = [{"paperId": "paper-1"}]

    assert _resolve_path(payload, "[0].paperId") == "paper-1"
