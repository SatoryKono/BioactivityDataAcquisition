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
"""Tests for metadata helpers."""

import pytest

import bioetl.infrastructure.storage.metadata.metadata_helpers as metadata_helpers


pytestmark = pytest.mark.unit


def test_build_and_validate_metadata_success():
    """Test build_and_validate_metadata function with valid data."""
    key = "test_key"
    value = "test_value"
    result = metadata_helpers.build_and_validate_metadata(key, value)
    assert result == {key: value}


def test_build_and_validate_metadata_failure():
    """Test build_and_validate_metadata function with empty metadata."""
    # Mock the metadata to be empty
    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "bioetl.infrastructure.storage.metadata.metadata_helpers._build_metadata",
            lambda x, y: {},
        )
        with pytest.raises(ValueError, match="Metadata is empty"):
            metadata_helpers.build_and_validate_metadata(
                "test_key",
                "test_value",
            )
