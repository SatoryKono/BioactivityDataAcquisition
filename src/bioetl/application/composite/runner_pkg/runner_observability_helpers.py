"""Free-function helpers for composite runner observability side effects."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any, Protocol, cast

from bioetl.application.composite.runner_pkg.runner_constants import (
    DQ_REPORT_NON_FATAL_ERRORS,
)
from bioetl.application.services.dq_report_service import DQReportService
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.composite.result import MergeResult
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.ports import LoggerPort, MetricsPort, QuarantinePort
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )

_COMPOSITE_CV_QUARANTINE_ARTIFACT_POLICY = "occurrence_only_diagnostic"
_COMPOSITE_CV_QUARANTINE_REPLAY_CONTRACT = "excluded_from_exact_replay"
_COMPOSITE_CV_QUARANTINE_SCOPE = "composite_cross_validation_quarantine"
_COMPOSITE_CV_QUARANTINE_RULE_ID = "composite.cross_validation.quarantine"
_COMPOSITE_CV_QUARANTINE_VIOLATION_KIND = "cross_validation_mismatch"

__all__ = [
    "CompositeRunnerObservabilityHostProtocol",
    "build_composite_cv_quarantine_metadata",
    "generate_dq_reports",
    "record_cv_quarantine_policy_if_supported",
    "resolve_composite_dq_timestamp",
]


class CompositeRunnerObservabilityHostProtocol(Protocol):
    _config: CompositeConfig = cast(Any, None)  # Any: host attr default (PD3)
    _logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD3)
    _run_id_str: str = cast(Any, None)  # Any: host attr default (PD3)
    _run_id: RunID = cast(Any, None)  # Any: host attr default (PD3)
    _runtime: object = cast(Any, None)  # Any: host attr default (PD3)
    _started_at: datetime | None = cast(Any, None)  # Any: host attr default (PD3)
    _dq_report_service: DQReportService | None = cast(
        Any, None
    )  # Any: host attr default (PD3)
    _quarantine_port: QuarantinePort | None = cast(
        Any, None
    )  # Any: host attr default (PD3)
    _metrics: MetricsPort | None = cast(Any, None)  # Any: host attr default (PD3)
    _run_ledger_service: RunLedgerService | None = cast(
        Any, None
    )  # Any: host attr default (PD3)

    def _record_with_ledger_service(
        self,
        recorder: Callable[[RunLedgerService], object],
    ) -> None: ...


def resolve_composite_dq_timestamp(
    *,
    cached_bronze_date: str | None,
    started_at: datetime | None,
) -> datetime:
    """Resolve a deterministic timestamp for composite DQ side effects."""
    if cached_bronze_date is not None:
        replay_date = date.fromisoformat(cached_bronze_date)
        return datetime.combine(replay_date, datetime.min.time(), tzinfo=UTC)
    if started_at is not None:
        return started_at
    return datetime(1970, 1, 1, tzinfo=UTC)


def build_composite_cv_quarantine_metadata() -> dict[str, object]:
    """Return the canonical replay policy for composite quarantine side effects."""
    return {
        "artifact_policy": _COMPOSITE_CV_QUARANTINE_ARTIFACT_POLICY,
        "replay_contract": _COMPOSITE_CV_QUARANTINE_REPLAY_CONTRACT,
        "diagnostic_scope": _COMPOSITE_CV_QUARANTINE_SCOPE,
        "violation_kind": _COMPOSITE_CV_QUARANTINE_VIOLATION_KIND,
        "semantic_artifact": False,
    }


def record_cv_quarantine_policy_if_supported(
    host: CompositeRunnerObservabilityHostProtocol,
    *,
    written: int,
    quarantine_metadata: dict[str, object],
) -> None:
    """Emit one control-plane policy event when the host exposes ledger wiring."""
    recorder = getattr(host, "_record_with_ledger_service", None)
    if not callable(recorder):
        return
    recorder(
        lambda ledger_service: ledger_service.record_dq_policy_applied(
            stage="cross_validation",
            status="quarantined",
            rule_id=_COMPOSITE_CV_QUARANTINE_RULE_ID,
            disposition="quarantine",
            details={
                "config_path": "cross_validation",
                "quarantine_record_count": written,
                **quarantine_metadata,
            },
        )
    )


async def generate_dq_reports(
    host: CompositeRunnerObservabilityHostProtocol,
    merge_result: MergeResult,
) -> None:
    """Generate DQ reports for composite pipeline."""
    if host._dq_report_service is None:
        host._logger.debug(
            "dq_reports_skipped",
            reason="DQReportService not configured",
            composite=host._config.name,
        )
        return

    try:
        from bioetl.application.services.dq_report_service import DQReportContext

        cached_bronze_date = cast(
            str | None,
            getattr(host._runtime, "cached_bronze_date", None),
        )
        dq_timestamp = resolve_composite_dq_timestamp(
            cached_bronze_date=cached_bronze_date,
            started_at=host._started_at,
        )
        context = DQReportContext(
            run_id=host._run_id_str,
            pipeline_name=f"composite_{host._config.name}",
            timestamp=dq_timestamp,
            provider="composite",
            entity=host._config.name,
            silver_target_table=host._config.merge.output_silver_path,
            silver_input_count=merge_result.records_from_seed,
            gold_target_table=host._config.merge.output_gold_path,
            dq_soft_threshold=host._config.dq.soft_fail_threshold,
            dq_hard_threshold=host._config.dq.hard_fail_threshold,
        )
        await host._dq_report_service.generate_reports(context)
        host._logger.info(
            "dq_reports_generated",
            composite=host._config.name,
            run_id=host._run_id_str,
        )
    except DQ_REPORT_NON_FATAL_ERRORS as error:
        host._logger.warning(
            "dq_reports_failed",
            composite=host._config.name,
            error=str(error),
            error_type=type(error).__name__,
        )
    except BioETLError as error:
        host._logger.warning(
            "dq_reports_failed",
            composite=host._config.name,
            error=str(error),
            error_type=type(error).__name__,
            reason_code="unexpected_bioetl_error",
        )
