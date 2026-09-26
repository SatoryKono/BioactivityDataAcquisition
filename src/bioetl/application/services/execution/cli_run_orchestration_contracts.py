"""Contracts for CLI run orchestration collaborators."""

from __future__ import annotations

from collections.abc import Coroutine
from typing import Any, Protocol

from bioetl.application.services.execution.cli_run_orchestration_models import (
    RunExecutionRequest,
)
from bioetl.application.services.execution.pipeline_runner_models import RunResult

__all__ = [
    "MetricsFlushCallable",
    "RunCoroutineCallable",
    "RunPreparedPipelineCallable",
]


class RunPreparedPipelineCallable(Protocol):
    """Callable contract for async execution of a prepared run request."""

    def __call__(
        self,
        request: RunExecutionRequest,
    ) -> Coroutine[Any, Any, RunResult]: ...  # Any: standard Coroutine type params


class RunCoroutineCallable(Protocol):
    """Callable contract to execute awaitables in sync context."""

    def __call__(
        self,
        main: Coroutine[Any, Any, RunResult],  # Any: standard Coroutine type params
        *,
        debug: bool | None = None,
    ) -> RunResult: ...


class MetricsFlushCallable(Protocol):
    """Callable contract for metrics flush at command boundary."""

    def __call__(
        self,
        run_label: str = "bioetl",
        *,
        pipeline_name: str | None = None,
        run_type: str | None = None,
    ) -> bool: ...
