"""Facade for the canonical execution seam."""

from __future__ import annotations

import warnings

from bioetl.application.services.execution.cli_run_orchestration_models import (
    CliRunOptionsInput,
    CliRunPreparationInput,
    RunExecutionRequest,
    RunPreparationResult,
    StartOffsetValidationResult,
)

_RUN_EXECUTION_CONTEXT_REMOVAL_DATE = "2026-09-30"

__all__ = [
    "CliRunOptionsInput",
    "CliRunPreparationInput",
    "RunExecutionContext",  # noqa: F822 - compatibility export resolved by __getattr__.
    "RunExecutionRequest",
    "RunPreparationResult",
    "StartOffsetValidationResult",
]


def __getattr__(name: str) -> object:
    """Serve compatibility exports that no longer exist canonically."""
    if name != "RunExecutionContext":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    warnings.warn(
        "RunExecutionContext is deprecated; use RunExecutionRequest instead. "
        f"Removal date: {_RUN_EXECUTION_CONTEXT_REMOVAL_DATE}.",
        DeprecationWarning,
        stacklevel=2,
    )
    return RunExecutionRequest


def __dir__() -> list[str]:
    """Keep deprecated compatibility names discoverable during transition."""
    return sorted(set(globals()) | {"RunExecutionContext"})
