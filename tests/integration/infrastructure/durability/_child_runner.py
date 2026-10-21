"""Run one durability probe in a fresh interpreter and return its exit code."""

from __future__ import annotations

import multiprocessing
from collections.abc import Callable

from tests.integration.infrastructure.durability.data_factories import (
    CHILD_FAILURE_CODE,
)


def child_exit_success() -> None:
    """Exit zero from a child process."""


def child_exit_failure() -> None:
    """Exit with the shared non-zero probe code."""
    raise SystemExit(CHILD_FAILURE_CODE)


def run_child(
    target: Callable[..., None],
    args: tuple[object, ...],
    *,
    timeout_s: float = 30.0,
) -> int:
    """Start ``target`` in a spawned process and return its exit code.

    A timed-out child is terminated and then killed. The caller receives
    ``TimeoutError`` instead of a hanging join.
    """
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    context = multiprocessing.get_context("spawn")
    process = context.Process(target=target, args=args)
    process.start()
    process.join(timeout_s)
    if process.is_alive():
        process.terminate()
        process.join(timeout_s)
        if process.is_alive():
            process.kill()
            process.join(timeout_s)
        raise TimeoutError(f"child exceeded {timeout_s} seconds")
    exit_code = process.exitcode
    if exit_code is None:
        raise RuntimeError("child finished without an exit code")
    return exit_code
