"""Compatibility facade for the canonical execution seam."""

from __future__ import annotations

from bioetl.application.services.execution.cli_run_orchestration_models import (
    RunExecutionRequest,
    RunPreparationResult,
    StartOffsetValidationResult,
)

# Compatibility alias for refactored naming
RunExecutionContext = RunExecutionRequest

__all__ = [
    "RunExecutionRequest",
    "RunPreparationResult",
    "RunExecutionContext",
    "StartOffsetValidationResult",
]
