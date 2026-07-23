"""ContextVar binding for per-run stage accounting."""

from __future__ import annotations

from contextvars import ContextVar, Token

from bioetl.domain.run_reports.accounting import StageAccountingAccumulator

_stage_accounting: ContextVar[StageAccountingAccumulator | None] = ContextVar(
    "bioetl_stage_accounting",
    default=None,
)


def get_stage_accounting() -> StageAccountingAccumulator | None:
    """Return the accumulator bound to the current run context, if any."""
    return _stage_accounting.get()


def bind_stage_accounting(
    accumulator: StageAccountingAccumulator,
) -> Token[StageAccountingAccumulator | None]:
    """Bind accumulator for the current context and return reset token."""
    return _stage_accounting.set(accumulator)


def reset_stage_accounting(
    token: Token[StageAccountingAccumulator | None],
) -> None:
    """Reset contextvar using the token from :func:`bind_stage_accounting`."""
    _stage_accounting.reset(token)
