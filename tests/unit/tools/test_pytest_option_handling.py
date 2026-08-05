"""Regression tests for supported pytest option metadata API variants."""

from __future__ import annotations

from types import SimpleNamespace

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
