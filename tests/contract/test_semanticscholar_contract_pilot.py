"""Richer Semantic Scholar pilot-soak contract checks.

These tests retain higher-signal assertions for the pilot provider but require
explicit soak opt-in so the promotion-grade baseline can stay lighter.
"""

from __future__ import annotations

import asyncio
import pytest
from tests.contract.test_semanticscholar_contract import EXPECTED_BATCH_IDENTITIES
from bioetl.domain.types import JsonDict

EXPECTED_DOIS = frozenset(EXPECTED_BATCH_IDENTITIES)
pytestmark = pytest.mark.no_api


@pytest.mark.semanticscholar
@pytest.mark.pilot_soak
@pytest.mark.timeout(300)
class TestSemanticScholarPilotContract:
    """Pilot-only Semantic Scholar assertions."""

    @pytest.mark.asyncio
    async def test_batch_lookup_preserves_doi_identity(
        self,
        semanticscholar_batch_payload: list[JsonDict | None],
    ) -> None:
        """Verify batch lookup still surfaces DOI identity metadata."""
        await asyncio.sleep(0)
        data = semanticscholar_batch_payload
        observed_dois: set[str] = set()
        for paper in data:
            assert isinstance(paper, dict)
            external_ids = paper.get("externalIds", {})
            assert isinstance(external_ids, dict)
            doi = external_ids.get("DOI")
            assert isinstance(doi, str)
            observed_dois.add(doi.lower())

        assert observed_dois == EXPECTED_DOIS

    @pytest.mark.asyncio
    async def test_semantic_scholar_pilot__health_probe_shape__ffa01178(
        self,
        semanticscholar_search_payload: JsonDict,
    ) -> None:
        """Verify search payload still exposes the minimal health-style shape."""
        await asyncio.sleep(0)
        data = semanticscholar_search_payload
        assert "data" in data
        assert isinstance(data["data"], list)
        assert "total" in data
