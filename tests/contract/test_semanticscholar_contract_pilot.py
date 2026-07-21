"""Richer Semantic Scholar pilot-soak contract checks.

These tests retain higher-signal assertions for the pilot provider but require
explicit soak opt-in so the promotion-grade baseline can stay lighter.
"""

from __future__ import annotations

import asyncio
import pytest
from bioetl.domain.types import JsonDict

# Fixtures live in tests/contract/conftest.py (imported from
# _semanticscholar_contract_support). Do not re-declare pytest_plugins here:
# a second plugin load after another module already imported the support
# package triggers PytestAssertRewriteWarning.
STABLE_DOI = "10.1038/s41586-020-2649-2"


@pytest.mark.semanticscholar
@pytest.mark.pilot_soak
@pytest.mark.timeout(300)
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
        assert external_ids.get("DOI", "").lower() == STABLE_DOI.lower()

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
