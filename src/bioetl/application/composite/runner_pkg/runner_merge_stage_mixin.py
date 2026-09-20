# Host attrs/methods provided by concrete composition (PD2 W1).
"""Merge/finalization stage helpers for CompositePipelineRunner."""

from __future__ import annotations

from typing import Any, cast

from bioetl.application.composite.checkpoint import CompositeCheckpointService
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.runner_pkg.runner_merge_request_flow import (
    execute_started_merge_phase as execute_started_merge_phase,
)
from bioetl.application.composite.runner_pkg.runner_merge_request_flow import (
    run_prepared_merge_request as run_prepared_merge_request,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_dispatch_mixin import (
    _CompositeRunnerMergeStageDispatchMixin,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_execution_mixin import (
    _CompositeRunnerMergeStageExecutionMixin,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_runtime import (
    handle_dry_run_merge_skip as handle_dry_run_merge_skip,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_runtime import (
    handle_merge_phase_exception as handle_merge_phase_exception,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_runtime import (
    start_merge_phase as start_merge_phase,
)
from bioetl.application.composite.runtime_models import (
    CompositeMergerProtocol,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.ports import LoggerPort

__all__ = ["CompositeRunnerMergeStageMixin"]


class CompositeRunnerMergeStageMixin(
    _CompositeRunnerMergeStageDispatchMixin,
    _CompositeRunnerMergeStageExecutionMixin,
):
    """Mixin containing merge execution and finalization."""

    _runtime: CompositeRuntimeConfig = cast(Any, None)  # Any: host attr default (PD3)
    _fsm: FSMStateHelperService = cast(Any, None)  # Any: host attr default (PD3)
    _logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD3)
    _config: CompositeConfig = cast(Any, None)  # Any: host attr default (PD3)
    _run_id_str: str = cast(Any, None)  # Any: host attr default (PD3)
    _merger: CompositeMergerProtocol = cast(Any, None)  # Any: host attr default (PD3)
    _checkpoint_manager: CompositeCheckpointService = cast(
        Any, None
    )  # Any: host attr default (PD3)
