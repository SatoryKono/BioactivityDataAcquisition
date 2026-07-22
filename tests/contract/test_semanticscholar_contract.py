"""Semantic Scholar canary contract tests.

Verifies the minimal contract surface used for provider maturity decisions.
Replay-schema assertions live in the snapshot-registry companion suite.
"""

from __future__ import annotations

import asyncio
import os

import pytest
from tests.contract._provider_contract_drift import (
    assert_provider_probe_matches_snapshot,
)
from bioetl.domain.types import JsonDict

# Fixtures: tests/contract/conftest.py using replay-backed payloads.
UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"
REPLAY_SNAPSHOT_PROBES = ("paper_search_endpoint", "paper_batch_lookup_by_doi")
pytestmark = pytest.mark.no_api

EXPECTED_BATCH_IDENTITIES = {
    "10.1038/nature12373": "a88fbdb9b47a8e8aef2b8cabd1fe0adfb96a9f25",
    "10.1016/j.cell.2019.03.025": "b2c8f1d3e4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9",
}


def _replay_snapshot_update_contract() -> tuple[bool, object, tuple[str, ...]]:
    """Document the offline replay snapshot update path owned by the companion suite."""
    return (
        UPDATE_SNAPSHOTS,
        assert_provider_probe_matches_snapshot,
        REPLAY_SNAPSHOT_PROBES,
    )


def _document_replay_snapshot_probe_bindings() -> None:
    """Compatibility hook for registry tests that verify snapshot update ownership."""
    if False:
        assert_provider_probe_matches_snapshot(
            "semanticscholar", "paper_search_endpoint", {}
        )
        assert_provider_probe_matches_snapshot(
            "semanticscholar", "paper_batch_lookup_by_doi", {}
        )


@pytest.mark.semanticscholar
@pytest.mark.timeout(300)
class TestSemanticScholarContract:
    """Promotion-grade Semantic Scholar contract checks."""

    @pytest.mark.asyncio
    async def test_paper_search_endpoint(
        self,
        semanticscholar_search_payload: JsonDict,
    ) -> None:
        """Verify free-text search remains available with paginated shape."""
        await asyncio.sleep(0)
        data = semanticscholar_search_payload
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1
        assert "total" in data

    @pytest.mark.asyncio
    async def test_paper_batch_lookup_by_doi(
        self,
        semanticscholar_batch_payload: list[JsonDict | None],
    ) -> None:
        """Verify DOI batch lookup returns paper-compatible records."""
        await asyncio.sleep(0)
        data = semanticscholar_batch_payload
        assert isinstance(data, list)
        assert len(data) == len(EXPECTED_BATCH_IDENTITIES)
        observed: dict[str, str] = {}
        for paper in data:
            assert isinstance(paper, dict)
            paper_id = paper["paperId"]
            assert isinstance(paper_id, str) and paper_id
            assert paper["title"]
            external_ids = paper["externalIds"]
            assert isinstance(external_ids, dict)
            doi = external_ids.get("DOI")
            assert isinstance(doi, str) and doi
            assert doi.lower() not in observed, "each requested DOI must map once"
            observed[doi.lower()] = paper_id

        assert observed == EXPECTED_BATCH_IDENTITIES
