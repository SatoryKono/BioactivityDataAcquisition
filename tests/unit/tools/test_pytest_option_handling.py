"""Regression tests for supported pytest option metadata API variants."""

from __future__ import annotations

import re
from types import SimpleNamespace
from unittest.mock import Mock

import syrupy
from syrupy.assertion import AssertionResult, DiffMode, SnapshotAssertion
from syrupy.extensions.amber import AmberSnapshotExtension

import pytest

from tests import conftest as root_conftest

pytestmark = pytest.mark.unit


def test_pytest_option_names_supports_callable_api() -> None:
    """pytest 9 exposes ``Argument.names`` as a method."""

    class CallableNamesOption:
        def names(self) -> tuple[str, ...]:
            return ("--vcr-record",)

    assert root_conftest._pytest_option_names(CallableNamesOption()) == (
        "--vcr-record",
    )


def test_pytest_option_names_supports_iterable_api() -> None:
    """Retain support for option objects exposing iterable names."""
    option = SimpleNamespace(names=("--vcr-record", "--vcr_record"))

    assert root_conftest._pytest_option_names(option) == (
        "--vcr-record",
        "--vcr_record",
    )


def test_snapshot_diff_option_preserves_enum_and_renders_mismatch(
    pytestconfig: pytest.Config,
) -> None:
    """The real controller/xdist worker config must retain Syrupy's Enum."""
    mode = pytestconfig.option.diff_mode
    assert isinstance(mode, DiffMode)
    location = Mock()
    assertion = SnapshotAssertion(
        session=Mock(),
        extension_class=AmberSnapshotExtension,
        test_location=location,
        update_snapshots=False,
    )
    assertion._executions = 1
    assertion._execution_results[0] = AssertionResult(
        snapshot_location="unused",
        snapshot_name="enum-regression",
        asserted_data="actual-marker",
        recalled_data="expected-marker",
        created=False,
        updated=False,
        success=False,
        exception=None,
        test_location=location,
    )

    explanation = syrupy.pytest_assertrepr_compare(
        config=pytestconfig, op="==", left=assertion, right="actual-marker"
    )

    assert explanation is not None
    details = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", "\n".join(explanation[1:]))
    if mode is DiffMode.DETAILED:
        assert "actual-marker" in details
        assert "expected-marker" in details
    else:
        assert mode is DiffMode.DISABLED
        assert details == ""
