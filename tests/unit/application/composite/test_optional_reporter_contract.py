"""Composite execution remains available without the optional parent reporter."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from tests.unit.application.composite.test_runner import create_runner

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_optional_reporter_absence_returns_the_original_execution_result(
    monkeypatch,
):
    runner = create_runner()
    runner._reporter = None
    result = object()
    execute = AsyncMock(return_value=result)
    monkeypatch.setattr(runner, "_run_with_lifecycle", execute)
    assert await runner.run() is result
    execute.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_parent_reporter_receives_the_exact_run_and_lifecycle_callback():
    runner = create_runner()
    result = object()
    execute = AsyncMock(return_value=result)
    runner._reporter = SimpleNamespace(execute=execute)
    assert await runner.run() is result
    execute.assert_awaited_once_with(runner.run_id, runner._run_with_lifecycle)
