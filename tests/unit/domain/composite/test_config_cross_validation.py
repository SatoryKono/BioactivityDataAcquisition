# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
from __future__ import annotations

import pytest

from bioetl.domain.composite.config_cross_validation import CrossValidationConfig
from bioetl.domain.composite.cross_validation import (
    ComparisonMethod,
    EnricherFieldPairing,
    FieldComparisonSpec,
)


pytestmark = pytest.mark.unit


def test_get_pairing_returns_matching_pipeline_pairing() -> None:
    pairing = EnricherFieldPairing(
        enricher_pipeline="crossref_publication",
        fields=(
            FieldComparisonSpec(
                field_name="title",
                method=ComparisonMethod.EXACT,
            ),
        ),
    )
    config = CrossValidationConfig(enricher_pairings=(pairing,))

    assert config.get_pairing("crossref_publication") == pairing


def test_get_pairing_returns_none_when_pipeline_is_not_configured() -> None:
    pairing = EnricherFieldPairing(
        enricher_pipeline="crossref_publication",
        fields=(
            FieldComparisonSpec(
                field_name="title",
                method=ComparisonMethod.EXACT,
            ),
        ),
    )
    config = CrossValidationConfig(enricher_pairings=(pairing,))

    assert config.get_pairing("openalex_publication") is None
