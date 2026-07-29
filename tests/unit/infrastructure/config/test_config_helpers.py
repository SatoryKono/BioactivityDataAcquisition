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
"""Tests for config helpers."""

import pytest

from bioetl.infrastructure.config.config_helpers import (
    load_and_validate_config,
    load_config,
)


pytestmark = pytest.mark.unit


def test_load_config_placeholder():
    """Test load_config function returns empty dict (placeholder)."""
    result = load_config("test_path")
    assert result == {}


def test_load_and_validate_config_success():
    """Test load_and_validate_config function with valid config."""
    # Mock the load_config function
    config = {"key": "value"}
    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "bioetl.infrastructure.config.config_helpers.load_config",
            lambda x: config,
        )
        result = load_and_validate_config("test_path")
        assert result == config


def test_load_and_validate_config_failure():
    """Test load_and_validate_config function with invalid config."""
    # Mock the load_config function to return None
    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "bioetl.infrastructure.config.config_helpers.load_config",
            lambda x: None,
        )
        with pytest.raises(ValueError, match="Config not found"):
            load_and_validate_config("test_path")
