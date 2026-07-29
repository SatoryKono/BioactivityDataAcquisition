# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Shared fixtures for CLI command tests.

Provides utilities for properly mocking asyncio.run in Click CLI tests.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch


def mock_asyncio_run(
    *,
    return_value: Any = None,
    side_effect: BaseException | type[BaseException] | None = None,
):
    """Create a ``patch("asyncio.run", ...)`` context manager that closes coroutines.

    When Click commands call ``asyncio.run(coroutine())``, and ``asyncio.run``
    is mocked, the coroutine object is created but never executed.  Python 3.13
    emits ``RuntimeWarning: coroutine ... was never awaited`` when the coroutine
    is garbage-collected.

    This helper properly closes the coroutine before returning / raising.

    Usage::

        with mock_asyncio_run(return_value=(True, None)):
            result = cli_runner.invoke(cli, ["run-composite", ...])

        with mock_asyncio_run(side_effect=KeyboardInterrupt()):
            result = cli_runner.invoke(cli, ["health", "server"])
    """

    def _run(coro: Any, **_kwargs: Any) -> Any:
        if asyncio.iscoroutine(coro):
            coro.close()
        if side_effect is not None:
            exc = side_effect() if isinstance(side_effect, type) else side_effect
            raise exc
        return return_value

    return patch("asyncio.run", side_effect=_run)
