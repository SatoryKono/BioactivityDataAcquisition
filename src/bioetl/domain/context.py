"""Domain execution context objects.

``PipelineRunContext`` carries launch-time state.
``PipelineContext`` carries in-run state.
There is no universal runtime manifest object.
Control-plane provenance remains separate via ``run_manifest.RunManifest``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from importlib import import_module
from typing import TYPE_CHECKING, Any

from bioetl.domain.context_cached_bronze import CachedBronzeContext
from bioetl.domain.context_filtering import InputFilterContext, VacuumSettings
from bioetl.domain.context_run import PipelineRunContext
from bioetl.domain.context_time import (
    MISSING_RUNTIME_TIMESTAMP,
    ClockLike,
    resolve_context_started_at,
)
from bioetl.domain.types import BatchID, RunID, RunType

if TYPE_CHECKING:
    from bioetl.domain.ports import ClockPort, LoggerPort
else:
    ClockPort = import_module("bioetl.domain.ports.runtime.clock").ClockPort
    LoggerPort = import_module("bioetl.domain.ports.observability.logging").LoggerPort

__all__ = [
    "MISSING_RUNTIME_TIMESTAMP",
    "CachedBronzeContext",
    "InputFilterContext",
    "PipelineContext",
    "PipelineRunContext",
    "VacuumSettings",
]


@dataclass(frozen=True, slots=True)
class PipelineContext:
    """In-run processing context for record, batch, and write execution paths."""

    run_id: RunID
    run_type: RunType
    logger: LoggerPort
    started_at: datetime = field(default=MISSING_RUNTIME_TIMESTAMP)
    source_batch_id: BatchID | None = None
    replay_timestamp_anchor: datetime | None = None
    pipeline_name: str | None = None
    workflow_id: str = "standalone"

    @classmethod
    def create(
        cls,
        run_id: RunID,
        run_type: RunType,
        logger: LoggerPort,
        started_at: datetime | None = None,
        clock: ClockLike | None = None,
        source_batch_id: BatchID | None = None,
        replay_timestamp_anchor: datetime | None = None,
        pipeline_name: str | None = None,
        workflow_id: str = "standalone",
    ) -> PipelineContext:
        """Create a new PipelineContext with explicit timestamp ownership."""
        return cls(
            run_id=run_id,
            run_type=run_type,
            logger=logger,
            started_at=resolve_context_started_at(
                started_at=started_at,
                clock=clock,
            ),
            source_batch_id=source_batch_id,
            replay_timestamp_anchor=replay_timestamp_anchor,
            pipeline_name=pipeline_name,
            workflow_id=workflow_id,
        )

    def bind_logger(
        self,
        **kwargs: Any,  # Any: structlog-compatible key=value pairs
    ) -> PipelineContext:
        """Bind additional context to the logger."""
        new_logger = self.logger.bind(**kwargs)
        return PipelineContext(
            run_id=self.run_id,
            run_type=self.run_type,
            logger=new_logger,
            started_at=self.started_at,
            source_batch_id=self.source_batch_id,
            replay_timestamp_anchor=self.replay_timestamp_anchor,
            pipeline_name=self.pipeline_name,
            workflow_id=self.workflow_id,
        )

    def with_source_batch_id(self, source_batch_id: BatchID | None) -> PipelineContext:
        """Return a new context with batch lineage set for the active transform path."""
        return PipelineContext(
            run_id=self.run_id,
            run_type=self.run_type,
            logger=self.logger,
            started_at=self.started_at,
            source_batch_id=source_batch_id,
            replay_timestamp_anchor=self.replay_timestamp_anchor,
            pipeline_name=self.pipeline_name,
            workflow_id=self.workflow_id,
        )
