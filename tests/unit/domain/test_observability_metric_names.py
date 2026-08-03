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
"""Unit coverage for canonical observability metric name helpers."""

from __future__ import annotations

import pytest

from bioetl.domain.observability_metric_names import (
    CANONICAL_OBSERVABILITY_METRIC_PREFIX,
    canonicalize_observability_metric_name,
    is_legacy_observability_metric_name,
)


pytestmark = pytest.mark.unit


def test_canonicalize_observability_metric_name_preserves_empty_and_canonical() -> None:
    assert CANONICAL_OBSERVABILITY_METRIC_PREFIX == "bioetl_"
    assert canonicalize_observability_metric_name("   ") == ""
    assert (
        canonicalize_observability_metric_name("bioetl_pipeline_started_total")
        == "bioetl_pipeline_started_total"
    )


def test_canonicalize_observability_metric_name_prefixes_legacy_name() -> None:
    assert (
        canonicalize_observability_metric_name(" pipeline_started_total ")
        == "bioetl_pipeline_started_total"
    )


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("pipeline_started_total", True),
        (" bioetl_pipeline_started_total ", False),
        ("", False),
        ("   ", False),
    ],
)
def test_is_legacy_observability_metric_name(name: str, expected: bool) -> None:
    assert is_legacy_observability_metric_name(name) is expected
