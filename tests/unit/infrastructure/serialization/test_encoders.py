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
"""Same-path owner tests for JSON encoder module."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.serialization.encoders import StdLibJsonEncoder, __all__


pytestmark = pytest.mark.unit


def test_stdlib_json_encoder_round_trips_compact_json() -> None:
    encoder = StdLibJsonEncoder()
    payload = {"b": 2, "a": 1}

    dumped = encoder.dumps(payload)

    assert dumped == '{"a":1,"b":2}'
    assert encoder.loads(dumped) == {"a": 1, "b": 2}


def test_stdlib_json_encoder_canonical_output_is_stable() -> None:
    encoder = StdLibJsonEncoder()

    assert encoder.dumps_canonical({"b": "beta", "a": "alpha"}) == (
        '{"a":"alpha","b":"beta"}'
    )
    assert "get_json_encoder" in __all__
