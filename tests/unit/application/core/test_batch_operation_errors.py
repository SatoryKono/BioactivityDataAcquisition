"""Coverage and contract tests for shared batch operation errors."""

from __future__ import annotations

import pytest

from bioetl.application.core import batch_runtime_failure_policy
from bioetl.application.core.batch_operation_errors import OPERATION_ERRORS
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
