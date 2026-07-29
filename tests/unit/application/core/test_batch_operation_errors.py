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
"""Coverage and contract tests for shared batch operation errors."""

from __future__ import annotations

import pytest

from bioetl.application.core import batch_runtime_failure_policy
from bioetl.application.core.batch_operation_errors import OPERATION_ERRORS
from bioetl.application.core.batch_operation_errors import is_operation_error
from bioetl.application.core.batch_operation_errors import operation_error_type_name
from bioetl.application.core.batch_processing_runtime import (
    OPERATION_ERRORS as RUNTIME_OPERATION_ERRORS,
)
from bioetl.domain.exceptions import BioETLError

pytestmark = pytest.mark.unit


def test_operation_errors_include_runtime_and_domain_failures() -> None:
    assert OPERATION_ERRORS == (
        BioETLError,
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
    )


def test_runtime_failure_policy_reexports_operation_errors() -> None:
    assert batch_runtime_failure_policy.OPERATION_ERRORS is OPERATION_ERRORS


def test_batch_processing_runtime_reexports_operation_errors() -> None:
    assert RUNTIME_OPERATION_ERRORS is OPERATION_ERRORS


def test_operation_error_policy_helpers_classify_and_name_errors() -> None:
    domain_error = BioETLError("domain failure")
    unexpected_error = LookupError("not part of batch operation policy")

    assert is_operation_error(domain_error) is True
    assert is_operation_error(unexpected_error) is False
    assert operation_error_type_name(domain_error) == "BioETLError"
