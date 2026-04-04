"""Private service accessor seam for CLI run command orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.services.cli_run_orchestration_service import (
        CliRunOrchestrationService,
    )

_cli_run_orchestration_service: CliRunOrchestrationService | None = None


def get_cli_run_orchestration_service() -> CliRunOrchestrationService:
    """Return process-local run orchestration service (lazy cached accessor seam)."""
    global _cli_run_orchestration_service
    if _cli_run_orchestration_service is None:
        from bioetl.application.services.cli_run_orchestration_service import (
            CliRunOrchestrationService,
        )

        _cli_run_orchestration_service = CliRunOrchestrationService()
    return _cli_run_orchestration_service


__all__ = ["get_cli_run_orchestration_service"]
