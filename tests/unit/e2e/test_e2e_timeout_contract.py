"""Unit guards for E2E timeout-budget invariants."""

from __future__ import annotations

import pytest

from tests.e2e import conftest as e2e_conftest

pytestmark = pytest.mark.unit


def test_windows_e2e_timeout_exceeds_inner_merge_budget() -> None:
    """Windows pytest timeout must exceed the inner Delta merge timeout."""
    outer_timeout = e2e_conftest._resolve_e2e_default_timeout(platform="win32")
    inner_timeout = e2e_conftest._resolve_e2e_merge_execution_timeout_seconds(
        platform="win32"
    )

    assert outer_timeout > inner_timeout
    assert inner_timeout == 180


def test_non_windows_e2e_timeout_exceeds_inner_merge_budget() -> None:
    """Non-Windows pytest timeout must also exceed the inner Delta merge timeout."""
    outer_timeout = e2e_conftest._resolve_e2e_default_timeout(platform="linux")
    inner_timeout = e2e_conftest._resolve_e2e_merge_execution_timeout_seconds(
        platform="linux"
    )

    assert outer_timeout > inner_timeout
    assert outer_timeout == 120
    assert inner_timeout == 90
