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
"""Same-path owner tests for source config normalizer module."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.config.source_normalizers.source import (
    normalize_source_config,
)


pytestmark = pytest.mark.unit


def test_normalize_source_config_rejects_retired_transport_aliases() -> None:
    raw = {
        "source": {
            "api": {
                "base_url": "https://example.org",
                "auth_type": "api_key",
                "api_key": "secret",
            },
            "client": {"timeout": 5},
            "rate_limit": {"with_api_key": {"requests_per_second": 2}},
        }
    }

    try:
        normalize_source_config(raw)
    except ValueError as error:
        assert "Retired source transport aliases" in str(error)
        assert "api, client" in str(error)
    else:
        raise AssertionError("Expected retired transport aliases to fail")


def test_normalize_source_config_rejects_retired_source_root_pagination_aliases() -> (
    None
):
    raw = {"source": {"batch_size": 100}}

    try:
        normalize_source_config(raw)
    except ValueError as error:
        assert "Retired source root pagination aliases" in str(error)
    else:
        raise AssertionError("Expected retired root pagination aliases to fail")
