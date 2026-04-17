"""Richer Semantic Scholar pilot-soak contract checks.

These tests retain higher-signal assertions for the pilot provider but require
explicit soak opt-in so the promotion-grade baseline can stay lighter.
"""

from __future__ import annotations

import asyncio
import pytest
from bioetl.domain.types import JsonDict
from tests.contract import _semanticscholar_contract_support as semanticscholar_support

pytest_plugins = ["tests.contract._semanticscholar_contract_support"]


@pytest.mark.semanticscholar
@pytest.mark.pilot_soak
@pytest.mark.timeout(120)
class TestSemanticScholarPilotContract:
    """Pilot-only Semantic Scholar live assertions."""

    @pytest.mark.asyncio
    async def test_batch_lookup_preserves_doi_identity(
        self,
        semanticscholar_batch_payload: list[JsonDict | None],
    ) -> None:
        """Verify batch lookup still surfaces DOI identity metadata."""
        await asyncio.sleep(0)
        data = semanticscholar_batch_payload
        paper = data[0]
        external_ids = paper.get("externalIds", {})
        assert isinstance(external_ids, dict)
        assert (
            external_ids.get("DOI", "").lower()
            == semanticscholar_support.STABLE_DOI.lower()
        )

    @pytest.mark.asyncio
    async def test_health_probe_shape(
        self,
        semanticscholar_search_payload: JsonDict,
    ) -> None:
        """Verify search payload still exposes the minimal health-style shape."""
        await asyncio.sleep(0)
        data = semanticscholar_search_payload
        assert "data" in data
        assert isinstance(data["data"], list)
        assert "total" in data
