"""Semantic Scholar promotion-grade contract tests.

Verifies the minimal live contract surface used for provider maturity decisions.
Richer Semantic Scholar checks live in the pilot-soak companion suite.
"""

from __future__ import annotations

import pytest
from bioetl.domain.types import JsonDict

pytest_plugins = ["tests.contract._semanticscholar_contract_support"]


@pytest.mark.semanticscholar
@pytest.mark.timeout(120)
class TestSemanticScholarContract:
    """Promotion-grade Semantic Scholar live contract checks."""

    @pytest.mark.asyncio
    async def test_paper_search_endpoint(
        self,
        semanticscholar_search_payload: JsonDict,
    ) -> None:
        """Verify free-text search remains available with paginated shape."""
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
        data = semanticscholar_batch_payload
        assert isinstance(data, list)
        assert len(data) == 1
        paper = data[0]
        assert isinstance(paper, dict)
        assert paper["paperId"]
        assert paper["title"]
        assert "externalIds" in paper
