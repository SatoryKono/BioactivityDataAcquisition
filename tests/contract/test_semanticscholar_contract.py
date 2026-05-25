"""Semantic Scholar promotion-grade contract tests.

Verifies the minimal live contract surface used for provider maturity decisions.
Richer Semantic Scholar checks live in the pilot-soak companion suite.
"""

from __future__ import annotations

import asyncio
import os

import pytest
from bioetl.domain.types import JsonDict

from tests.contract._provider_contract_drift import (
    assert_provider_probe_matches_snapshot,
)

pytest_plugins = ["tests.contract._semanticscholar_contract_support"]
UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"


@pytest.mark.semanticscholar
@pytest.mark.timeout(300)
class TestSemanticScholarContract:
    """Promotion-grade Semantic Scholar live contract checks."""

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
    async def test_paper_search_snapshot_contract(
        self,
        semanticscholar_search_payload: JsonDict,
    ) -> None:
        """Verify free-text search payload matches the managed snapshot."""
        await asyncio.sleep(0)
        assert_provider_probe_matches_snapshot(
            "semanticscholar",
            "paper_search_endpoint",
            semanticscholar_search_payload,
            update_snapshots=UPDATE_SNAPSHOTS,
        )

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

    @pytest.mark.asyncio
    async def test_paper_batch_lookup_snapshot_contract(
        self,
        semanticscholar_batch_payload: list[JsonDict | None],
    ) -> None:
        """Verify DOI batch lookup payload matches the managed snapshot."""
        await asyncio.sleep(0)
        assert_provider_probe_matches_snapshot(
            "semanticscholar",
            "paper_batch_lookup_by_doi",
            semanticscholar_batch_payload,
            update_snapshots=UPDATE_SNAPSHOTS,
        )
