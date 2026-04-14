"""Compatibility facade for the canonical execution seam."""

from __future__ import annotations

from bioetl.application.services.execution.cli_run_orchestration_service import (
    CliRunOrchestrationService,
    MetricsFlushCallable,
    RunCoroutineCallable,
    RunExecutionRequest,
    RunPreparationResult,
    RunPreparedPipelineCallable,
    StartOffsetValidationResult,
)

__all__ = [
    "CliRunOrchestrationService",
    "MetricsFlushCallable",
    "RunCoroutineCallable",
    "RunExecutionRequest",
    "RunPreparationResult",
    "RunPreparedPipelineCallable",
    "StartOffsetValidationResult",
]
