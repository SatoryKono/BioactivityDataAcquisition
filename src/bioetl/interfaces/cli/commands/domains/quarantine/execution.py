"""Execution policy helpers for quarantine CLI commands."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass

from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CliBoundaryExecutionPolicy,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    run_async_with_cli_failure_policy,
    run_sync_with_cli_failure_policy,
)

__all__ = [
    "QuarantineExecutionPolicy",
    "run_quarantine_async",
    "run_quarantine_sync",
]

@dataclass(frozen=True, slots=True)
class QuarantineExecutionPolicy:
    """Typed execution policy for one quarantine CLI operation."""

    pipeline: str
    reason_prefix: str
    domain_error_title: str
    unexpected_error_title: str
    interrupted_message: str = "Quarantine command interrupted by user (Ctrl+C)"
def _shared_policy(policy: QuarantineExecutionPolicy) -> CliBoundaryExecutionPolicy:
    """Convert the quarantine policy to the shared CLI boundary policy."""
    return CliBoundaryExecutionPolicy(
        reason_prefix=policy.reason_prefix,
        subject_key="pipeline",
        subject_value=policy.pipeline,
        domain_error_title=policy.domain_error_title,
        unexpected_error_title=policy.unexpected_error_title,
        interrupted_message=policy.interrupted_message,
    )


def run_quarantine_async[T](
    coro: Coroutine[object, object, T],
    *,
    policy: QuarantineExecutionPolicy,
) -> T | None:
    """Run an async quarantine coroutine with typed exception policy."""
    return run_async_with_cli_failure_policy(coro, policy=_shared_policy(policy))


def run_quarantine_sync[T](
    fn: Callable[[], T],
    *,
    policy: QuarantineExecutionPolicy,
) -> T | None:
    """Run a synchronous quarantine callable with typed exception policy."""
    return run_sync_with_cli_failure_policy(fn, policy=_shared_policy(policy))
