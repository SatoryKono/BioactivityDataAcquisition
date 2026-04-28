"""Execution policy helpers for quarantine CLI commands."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import TypeVar

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode

__all__ = [
    "QuarantineExecutionPolicy",
    "run_quarantine_async",
    "run_quarantine_sync",
]

_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class QuarantineExecutionPolicy:
    """Typed execution policy for one quarantine CLI operation."""

    pipeline: str
    reason_prefix: str
    domain_error_title: str
    unexpected_error_title: str
    interrupted_message: str = "Quarantine command interrupted by user (Ctrl+C)"


def _handle_quarantine_failure(
    exc: BaseException,
    *,
    policy: QuarantineExecutionPolicy,
    reason_suffix: str,
) -> None:
    """Handle quarantine command failures with shared CLI policy."""
    handle_cli_execution_failure(
        exc,
        reason_code=f"{policy.reason_prefix}_{reason_suffix}",
        subject_key="pipeline",
        subject_value=policy.pipeline,
        domain_error_title=policy.domain_error_title,
        unexpected_error_title=policy.unexpected_error_title,
        interrupted_message=policy.interrupted_message,
        default_exit_code=ExitCode.FAIL,
    )


def run_quarantine_async[T](
    coro: Coroutine[object, object, _T],
    *,
    policy: QuarantineExecutionPolicy,
) -> _T | None:
    """Run an async quarantine coroutine with typed exception policy."""
    try:
        return asyncio.run(coro)
    except BioETLError as exc:
        _handle_quarantine_failure(
            exc,
            policy=policy,
            reason_suffix="DOMAIN_ERROR",
        )
    except KeyboardInterrupt as exc:
        _handle_quarantine_failure(
            exc,
            policy=policy,
            reason_suffix="SIGINT",
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_quarantine_failure(
            exc,
            policy=policy,
            reason_suffix="UNEXPECTED_ERROR",
        )
    finally:
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()
    return None


def run_quarantine_sync[T](
    fn: Callable[[], _T],
    *,
    policy: QuarantineExecutionPolicy,
) -> _T | None:
    """Run a synchronous quarantine callable with typed exception policy."""
    try:
        return fn()
    except BioETLError as exc:
        _handle_quarantine_failure(
            exc,
            policy=policy,
            reason_suffix="DOMAIN_ERROR",
        )
    except KeyboardInterrupt as exc:
        _handle_quarantine_failure(
            exc,
            policy=policy,
            reason_suffix="SIGINT",
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_quarantine_failure(
            exc,
            policy=policy,
            reason_suffix="UNEXPECTED_ERROR",
        )
    return None
