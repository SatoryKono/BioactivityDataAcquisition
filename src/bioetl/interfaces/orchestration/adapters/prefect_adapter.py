"""Prefect Adapter for OrchestrationPort.

Implements the OrchestrationPort using Prefect as the workflow engine.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING
import asyncio

if TYPE_CHECKING:
    from bioetl.domain.ports import OrchestrationPort
    from bioetl.domain.types import RunID


class PrefectOrchestrationAdapter:
    """Adapter for Prefect orchestration engine.

    This class adapts the generic OrchestrationPort interface to specific
    Prefect calls. Since this project currently uses a custom runner and
    Prefect is a dependency but not fully utilized for orchestration logic
    in the core loop (yet), this serves as a bridge.
    """

    async def schedule(
        self,
        pipeline_name: str,
        schedule: str,
        params: dict[str, Any] | None = None
    ) -> None:
        """Schedule a pipeline execution."""
        # Stub implementation for now as we don't have a full Prefect server setup
        pass

    async def trigger(
        self,
        pipeline_name: str,
        params: dict[str, Any] | None = None
    ) -> RunID:
        """Trigger an immediate pipeline execution."""
        from uuid import uuid4
        from bioetl.domain.types import RunID

        # In a real implementation, this would call prefect.deployments.run_deployment
        return RunID(uuid4())

    async def get_status(self, run_id: RunID) -> str:
        """Get the status of a pipeline run."""
        return "UNKNOWN"

    async def aclose(self) -> None:
        """Close connection to orchestration backend."""
        pass
