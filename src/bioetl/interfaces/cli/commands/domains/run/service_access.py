"""Private service accessor seam for CLI run command orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.services.execution.cli_run_orchestration_service import (
        CliRunOrchestrationService,
    )

_cli_run_orchestration_service: CliRunOrchestrationService | None = None


def create_cli_run_orchestration_service() -> CliRunOrchestrationService:
    """Build a fresh run orchestration service for one CLI command execution."""
    from bioetl.application.services.execution.cli_run_orchestration_service import (
        CliRunOrchestrationService,
    )

    return CliRunOrchestrationService()


def get_cli_run_orchestration_service() -> CliRunOrchestrationService:
    """Return process-local run orchestration service compatibility accessor."""
    global _cli_run_orchestration_service
    if _cli_run_orchestration_service is None:
        _cli_run_orchestration_service = create_cli_run_orchestration_service()
    return _cli_run_orchestration_service


__all__ = [
    "create_cli_run_orchestration_service",
    "get_cli_run_orchestration_service",
]
