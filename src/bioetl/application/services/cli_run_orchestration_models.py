"""Compatibility facade for the canonical execution seam."""

from __future__ import annotations

from bioetl.application.services.execution.cli_run_orchestration_models import (
    CliRunOptionsInput,
    CliRunPreparationInput,
    RunExecutionRequest,
    RunPreparationResult,
    StartOffsetValidationResult,
)

# Compatibility alias for refactored naming
RunExecutionContext = RunExecutionRequest

__all__ = [
    "CliRunOptionsInput",
    "CliRunPreparationInput",
    "RunExecutionContext",
    "RunExecutionRequest",
    "RunPreparationResult",
    "StartOffsetValidationResult",
]
