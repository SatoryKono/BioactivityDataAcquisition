# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Support helpers for composite runner stage orchestration."""

from __future__ import annotations

from bioetl.application.composite.runner_pkg.runner_stage_support_dispatch_mixin import (
    _CompositeRunnerStageSupportDispatchMixin,
)
from bioetl.application.composite.runner_pkg.runner_stage_support_flow_mixin import (
    _CompositeRunnerStageSupportFlowMixin,
)

__all__ = ["_CompositeRunnerStageSupportMixin"]


class _CompositeRunnerStageSupportMixin(
    _CompositeRunnerStageSupportDispatchMixin,
    _CompositeRunnerStageSupportFlowMixin,
):
    """Shared helper calls and small guards for stage orchestration."""
