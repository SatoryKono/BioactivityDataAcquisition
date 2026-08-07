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
"""Tests for logging helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.observability.logging_helpers import log_debug, log_error


pytestmark = pytest.mark.unit


def test_log_error():
    """Test log_error function."""
    logger = MagicMock()
    error = "Test error"
    log_error(logger, error)
    logger.error.assert_called_once_with("error_occurred", error=error)


def test_log_debug():
    """Test log_debug function."""
    logger = MagicMock()
    details = "Test details"
    log_debug(logger, details)
    logger.debug.assert_called_once_with("debug_info", details=details)
