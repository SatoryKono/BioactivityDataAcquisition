"""Thread-safe context management for ApplicationContext.

This module provides contextvars-based context management that allows
for thread-safe and async-safe scoping of ApplicationContext.

Key benefits:
- Thread-safe: Each thread can have its own context
- Async-safe: Works correctly with asyncio
- Testable: Easy to inject mock contexts in tests
- Scoped: Context is automatically cleaned up when scope exits

Usage:
    # Production - uses global singleton
    ctx = get_current_context()
    use_case = ctx.use_case_factory.create_run_pipeline_use_case()

    # Testing - scoped context
    with application_context(mock_context):
        # All calls to get_current_context() return mock_context
        result = function_under_test()
    # Original context is restored after the block

    # Async-safe
    async def process_request():
        ctx = get_current_context()
        # Each async task can have its own context
"""

from __future__ import annotations

from contextlib import contextmanager
import contextvars
from typing import TYPE_CHECKING, Generator

if TYPE_CHECKING:
    from bioetl.interfaces.application_context import ApplicationContext

# Context variable for thread-safe/async-safe context storage
_current_context: contextvars.ContextVar[ApplicationContext | None] = (
    contextvars.ContextVar("bioetl_app_context", default=None)
)


def get_current_context() -> "ApplicationContext":
    """Get the current application context.

    This function returns the context for the current thread/async task.
    If no context is set, it lazily creates the default context.

    Returns:
        Current ApplicationContext instance.

    Raises:
        RuntimeError: If context initialization fails.

    Example:
        >>> ctx = get_current_context()
        >>> logger = ctx.logger
    """
    ctx = _current_context.get()
    if ctx is None:
        # Lazy initialization - create default context
        from bioetl.interfaces.application_context import ApplicationContext

        ctx = ApplicationContext.create_default()
        _current_context.set(ctx)
    return ctx


def set_current_context(ctx: "ApplicationContext") -> None:
    """Set the current application context.

    This function sets the context for the current thread/async task.
    Use the application_context() context manager for automatic cleanup.

    Args:
        ctx: ApplicationContext to set as current.

    Example:
        >>> set_current_context(custom_context)
        >>> # Now get_current_context() returns custom_context
    """
    _current_context.set(ctx)


def reset_current_context() -> None:
    """Reset the current context to None.

    After calling this, the next call to get_current_context() will
    create a new default context.
    """
    _current_context.set(None)


@contextmanager
def application_context(
    ctx: "ApplicationContext",
) -> Generator["ApplicationContext", None, None]:
    """Context manager for scoped application context.

    This context manager allows temporarily overriding the current context.
    The previous context is automatically restored when the block exits.

    This is particularly useful for:
    - Testing with mock dependencies
    - Running code with different configurations
    - Isolating async tasks

    Args:
        ctx: ApplicationContext to use within the scope.

    Yields:
        The provided ApplicationContext.

    Example:
        >>> mock_ctx = ApplicationContext(...)
        >>> with application_context(mock_ctx):
        ...     # All code here uses mock_ctx
        ...     result = function_under_test()
        >>> # Original context is restored
    """
    token = _current_context.set(ctx)
    try:
        yield ctx
    finally:
        _current_context.reset(token)


__all__ = [
    "application_context",
    "get_current_context",
    "reset_current_context",
    "set_current_context",
]
