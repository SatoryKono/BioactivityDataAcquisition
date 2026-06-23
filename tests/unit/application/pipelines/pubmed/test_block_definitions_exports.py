"""Regression tests for the split PubMed block registry barrel."""

from __future__ import annotations

import pytest

from bioetl.application.pipelines.pubmed import block_definitions
from bioetl.application.pipelines.pubmed._block_definitions_analytics import (
    _PubMedClassificationBlock,
    _PubMedDateBlock,
    _PubMedMetricsBlock,
)
from bioetl.application.pipelines.pubmed._block_definitions_base import _PubMedXmlBlock
from bioetl.application.pipelines.pubmed._block_definitions_edition import (
    _PubMedAuthorBlock,
    _PubMedJournalBlock,
)
from bioetl.application.pipelines.pubmed._block_definitions_identifiers import (
    _PubMedCoreBlock,
    _PubMedIdentifierBlock,
)


pytestmark = pytest.mark.unit


def test_block_definitions_barrel_preserves_split_block_exports() -> None:
    """Compatibility barrel should keep importing the split provider-owned blocks."""
    assert block_definitions._PubMedAuthorBlock is _PubMedAuthorBlock
    assert block_definitions._PubMedClassificationBlock is _PubMedClassificationBlock
    assert block_definitions._PubMedCoreBlock is _PubMedCoreBlock
    assert block_definitions._PubMedDateBlock is _PubMedDateBlock
    assert block_definitions._PubMedIdentifierBlock is _PubMedIdentifierBlock
    assert block_definitions._PubMedJournalBlock is _PubMedJournalBlock
    assert block_definitions._PubMedMetricsBlock is _PubMedMetricsBlock
    assert block_definitions._PubMedXmlBlock is _PubMedXmlBlock
    assert set(block_definitions.__all__) == {
        "_PubMedAuthorBlock",
        "_PubMedClassificationBlock",
        "_PubMedCoreBlock",
        "_PubMedDateBlock",
        "_PubMedIdentifierBlock",
        "_PubMedJournalBlock",
        "_PubMedMetricsBlock",
        "_PubMedXmlBlock",
    }
