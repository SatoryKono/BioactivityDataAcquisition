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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
