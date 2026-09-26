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
"""Unit tests for publication assembly normalization seams."""

from __future__ import annotations

import pytest

from typing import Any

from bioetl.application.pipelines.common.publication_assembly import (
    normalize_publication_business_data,
)


pytestmark = pytest.mark.unit


class _StubNormalizer:
    def __init__(self, normalized: dict[str, Any]) -> None:
        self.normalized = normalized

    def normalize_business_data(self, business_data: dict[str, Any]) -> dict[str, Any]:
        return dict(self.normalized)


class _StubTransformer:
    def __init__(self, normalized: dict[str, Any]) -> None:
        self._record_normalizer = _StubNormalizer(normalized)


def test_normalize_publication_business_data_keeps_canonical_issn_string_payload() -> (
    None
):
    transformer = _StubTransformer(
        {
            "issn": "1234-5678",
            "issn_list": '["1234-5678","2049-3630"]',
        }
    )

    normalized = normalize_publication_business_data(
        transformer,
        {"issn": ["1234-5678", "2049-3630"]},
    )

    assert normalized["issn"] == "1234-5678"
    assert normalized["issn_list"] == '["1234-5678","2049-3630"]'
    assert not isinstance(normalized["issn"], list)


def test_normalize_publication_business_data_does_not_restore_native_issn_list() -> (
    None
):
    transformer = _StubTransformer({"issn": '["1234-5678","2049-3630"]'})

    normalized = normalize_publication_business_data(
        transformer,
        {"issn": ["1234-5678", "2049-3630"]},
    )

    assert normalized["issn"] == '["1234-5678","2049-3630"]'
    assert not isinstance(normalized["issn"], list)
