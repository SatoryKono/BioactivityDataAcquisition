"""Reject malformed executor policies before starting a provider worker."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.pubchem.fetch_flow import (
    ExecutorTimeoutState,
    coerce_executor_timeout,
    coerce_timeout_state,
    wait_for_executor,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("value", [True, "30", object()])
def test_timeout_requires_numeric_policy(value):
    with pytest.raises(TypeError, match="positive number"):
        coerce_executor_timeout(value)


@pytest.mark.parametrize("value", [0, -1.0])
def test_timeout_requires_positive_duration(value):
    with pytest.raises(ValueError, match="must be positive"):
        coerce_executor_timeout(value)


def test_timeout_state_rejects_unowned_mutable_flags():
    with pytest.raises(TypeError, match="ExecutorTimeoutState"):
        coerce_timeout_state({"timed_out": False})


@pytest.mark.asyncio
async def test_absent_deadline_preserves_worker_result_and_state():
    state = ExecutorTimeoutState()
    expected = object()

    async def worker():
        return expected

    assert await wait_for_executor(worker(), None, state) is expected
    assert state.timed_out is False
