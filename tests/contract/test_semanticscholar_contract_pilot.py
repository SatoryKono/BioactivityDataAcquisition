# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
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
