# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Observability and quarantine helpers for CompositePipelineRunner."""

from __future__ import annotations

from typing import Any, cast

from bioetl.application.composite.runner_pkg.runner_cv_quarantine_helpers import (
    write_cv_quarantine,
)
from bioetl.application.composite.runner_pkg.runner_observability_helpers import (
    CompositeRunnerObservabilityHostProtocol,
    generate_dq_reports,
)
from bioetl.application.services.quality.dq_report_service import DQReportService
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.composite.result import MergeResult
from bioetl.domain.ports import LoggerPort, MetricsPort, QuarantinePort
from bioetl.domain.types import RunID

__all__ = ["CompositeRunnerObservabilityMixin"]


class CompositeRunnerObservabilityMixin:
    """Mixin with optional DQ reporting and quarantine side effects."""

    _config: CompositeConfig = cast(Any, None)  # Any: host attr default (PD3)
    _logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD3)
    _run_id_str: str = cast(Any, None)  # Any: host attr default (PD3)
    _run_id: RunID = cast(Any, None)  # Any: host attr default (PD3)
    _dq_report_service: DQReportService | None = cast(
        Any, None
    )  # Any: host attr default (PD3)
    _quarantine_port: QuarantinePort | None = cast(
        Any, None
    )  # Any: host attr default (PD3)
    _metrics: MetricsPort | None = cast(Any, None)  # Any: host attr default (PD3)

    async def _generate_dq_reports(
        self: CompositeRunnerObservabilityHostProtocol,
        merge_result: MergeResult,
    ) -> None:
        """Generate DQ reports for composite pipeline.

        Args:
            merge_result: Merge execution result providing table paths and record counts
                used to populate the DQ report context.
        """
        await generate_dq_reports(self, merge_result)

    async def _write_cv_quarantine(
        self: CompositeRunnerObservabilityHostProtocol,
        merge_result: MergeResult,
    ) -> None:
        """Write cross-validation quarantine records if any exist.

        Args:
            merge_result: Merge result containing ``quarantine_payloads`` from
                cross-validation. When empty or quarantine port is absent, no writes occur.
        """
        await write_cv_quarantine(self, merge_result)
