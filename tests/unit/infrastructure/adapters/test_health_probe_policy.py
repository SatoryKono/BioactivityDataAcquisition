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
"""Unit tests for shared health probe latency policy."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.health_probe_policy import (
    DEFAULT_SLOW_HEALTH_PROBE_THRESHOLD_SECONDS,
    is_slow_health_probe,
)

pytestmark = pytest.mark.unit


def test_is_slow_health_probe_uses_default_threshold() -> None:
    assert DEFAULT_SLOW_HEALTH_PROBE_THRESHOLD_SECONDS == pytest.approx(5.0)
    assert not is_slow_health_probe(elapsed_seconds=5.0)
    assert is_slow_health_probe(elapsed_seconds=5.01)


def test_is_slow_health_probe_supports_custom_threshold() -> None:
    assert not is_slow_health_probe(elapsed_seconds=1.5, slow_threshold_seconds=2.0)
    assert is_slow_health_probe(elapsed_seconds=2.1, slow_threshold_seconds=2.0)
