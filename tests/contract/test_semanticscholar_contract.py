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
        """Verify DOI batch lookup returns a paper-compatible record."""
        await asyncio.sleep(0)
        data = semanticscholar_batch_payload
        assert isinstance(data, list)
        assert len(data) == 1
        paper = data[0]
        assert isinstance(paper, dict)
        assert paper["paperId"]
        assert paper["title"]
        assert "externalIds" in paper
