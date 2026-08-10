# pyright: reportArgumentType=false
"""Unit tests for adapter health check contract."""

from __future__ import annotations

import time

import pytest

from bioetl.infrastructure.adapters.common.error_bundles import (
    COMMON_ADAPTER_HEALTH_ERRORS_WITH_KEYERROR,
)
from bioetl.infrastructure.adapters.health_check_contract import (
    HEALTH_CHECK_ERRORS,
    HealthCheckContext,
)

pytestmark = pytest.mark.unit


def test_health_check_errors_alias() -> None:
    """Ensure HEALTH_CHECK_ERRORS is an alias to COMMON_ADAPTER_HEALTH_ERRORS_WITH_KEYERROR."""
    assert HEALTH_CHECK_ERRORS is COMMON_ADAPTER_HEALTH_ERRORS_WITH_KEYERROR


def test_health_check_context_defaults() -> None:
    """Ensure HealthCheckContext initializes with expected defaults."""
    t1 = time.monotonic()
    context = HealthCheckContext()
    t2 = time.monotonic()

    assert t1 <= context.start_time <= t2
    assert context.provider == ""
    assert context.endpoint == ""


def test_health_check_context_elapsed_seconds() -> None:
    """Ensure elapsed_seconds calculates correctly based on monotonic time."""
    context = HealthCheckContext(start_time=time.monotonic() - 5.5)
    elapsed = context.elapsed_seconds

    assert elapsed >= 5.5
    assert elapsed < 6.0


def test_health_check_context_custom_values() -> None:
    """Ensure HealthCheckContext accepts custom values."""
    context = HealthCheckContext(
        start_time=50.0, provider="test_provider", endpoint="https://example.test"
    )

    assert context.start_time == 50.0
    assert context.provider == "test_provider"
    assert context.endpoint == "https://example.test"
