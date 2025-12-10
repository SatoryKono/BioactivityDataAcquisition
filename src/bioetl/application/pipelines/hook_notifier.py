"""Hook notification component for pipeline stage events."""

from collections.abc import Iterable
from datetime import datetime, timezone

from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext, StageResult
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.pipelines.contracts import PipelineHookABC


class HookNotifier:
    """Manages hook registration and notification for pipeline stage events."""

    def __init__(
        self,
        *,
        logger: LoggingPortABC,
        pipeline_id: str | None = None,
        hooks: Iterable[PipelineHookABC] | None = None,
    ) -> None:
        self._logger = logger
        self._pipeline_id = pipeline_id
        self._hooks: list[PipelineHookABC] = list(hooks or [])
        self._stage_starts: dict[str, datetime] = {}
        self._current_run_id: str | None = None

    @property
    def current_run_id(self) -> str | None:
        """Return the current run ID."""
        return self._current_run_id

    def set_logger(self, logger: LoggingPortABC) -> None:
        """Update the logger instance."""
        self._logger = logger

    def register_hook(self, hook: PipelineHookABC) -> None:
        """Register a single hook."""
        self._hooks.append(hook)

    def register_hooks(self, hooks: Iterable[PipelineHookABC]) -> None:
        """Register multiple hooks."""
        for hook in hooks:
            self.register_hook(hook)

    def get_hooks(self) -> list[PipelineHookABC]:
        """Return list of registered hooks."""
        return self._hooks

    def notify_stage_start(
        self,
        stage: str,
        context: RunContext,
        *,
        provider: str,
        entity_name: str,
    ) -> None:
        """Notify hooks about stage start and log the event."""
        self._stage_starts[stage] = datetime.now(timezone.utc)
        self._current_run_id = context.run_id
        self._logger.info(
            "Stage started",
            provider=context.provider,
            entity=context.entity_name,
            run_id=context.run_id,
            stage=stage,
            pipeline=self._pipeline_id,
        )
        for hook in self._hooks:
            hook.on_stage_start(stage, context)

    def notify_stage_end(
        self,
        stage: str,
        result: StageResult,
        *,
        provider: str,
        entity_name: str,
    ) -> None:
        """Notify hooks about stage completion and log the event."""
        self._logger.info(
            "Stage finished",
            records=result.records_processed,
            chunks=result.chunks_processed,
            provider=provider,
            entity=entity_name,
            stage=stage,
            pipeline=self._pipeline_id,
            run_id=self._current_run_id,
            outcome="success" if result.success else "error",
        )
        for hook in self._hooks:
            hook.on_stage_end(stage, result)

    def notify_stage_error(
        self,
        stage: str,
        error: PipelineStageError,
    ) -> None:
        """Notify hooks about stage error."""
        for hook in self._hooks:
            hook.on_error(stage, error)

    def get_stage_start(self, stage: str) -> datetime | None:
        """Return the recorded start time for a stage, if any."""
        return self._stage_starts.get(stage)

    def reset(self) -> None:
        """Clear accumulated state."""
        self._stage_starts.clear()
        self._current_run_id = None
