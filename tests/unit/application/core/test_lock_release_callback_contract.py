"""Lock cleanup may be invoked from an event-loop callback without a Task."""

import asyncio

import pytest

from bioetl.application.core.lifecycle.lock_lifecycle import _clear_task_cancellation

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_no_task_cleanup_callback_does_not_raise_or_cancel_caller():
    loop = asyncio.get_running_loop()
    completed = loop.create_future()

    def callback():
        try:
            assert asyncio.current_task() is None
            _clear_task_cancellation()
        except Exception as exc:
            completed.set_exception(exc)
            return
        completed.set_result(True)

    loop.call_soon(callback)
    assert await completed is True
    assert asyncio.current_task().cancelling() == 0
