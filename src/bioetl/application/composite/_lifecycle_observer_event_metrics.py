"""Composite lifecycle event and metric helpers."""

from __future__ import annotations

from bioetl.application.composite._lifecycle_observer_tracing_types import (
    _CompositeLifecycleTracingHost,
)
from bioetl.domain.observability_contract import build_observability_contract_payload


class CompositeLifecycleEventMetricsMixin:
    """Event-emission and metric helpers for composite lifecycle flows."""

    @staticmethod
    def _normalize_severity(level: str) -> str:
        """Normalize severity to the bounded contract vocabulary."""
        normalized = level.strip().lower()
        if normalized in {"debug", "info", "warning", "error"}:
            return normalized
        return "info"

    @staticmethod
    def _pipeline_name(composite_name: str) -> str:
        """Return the canonical composite pipeline name for observability."""
        return f"composite:{composite_name}"

    @staticmethod
    def _filter_reserved_context(
        context: dict[str, object],
        *,
        reserved_keys: set[str] | None = None,
    ) -> dict[str, object]:
        """Drop reserved contract keys from caller-provided event context."""
        reserved = reserved_keys or {"composite", "run_id"}
        return {key: value for key, value in context.items() if key not in reserved}

    def _emit_contract_event(
        self: _CompositeLifecycleTracingHost,
        event_name: str,
        *,
        composite_name: str,
        run_id: str,
        severity: str,
        **context: object,
    ) -> None:
        """Emit one lifecycle event through the canonical observability contract."""
        normalized_severity = self._normalize_severity(severity)
        payload = build_observability_contract_payload(
            event_name=event_name,
            context=context,
            default_provider="composite",
            default_pipeline=self._pipeline_name(composite_name),
            default_run_id=run_id,
            default_severity=normalized_severity,
            correlation_defaults={
                "entity": composite_name,
                "run_type": "composite",
                "composite_run_id": run_id,
            },
        )
        log_context = dict(payload.context)
        log_context.pop("event", None)
        log_method = getattr(self.logger, normalized_severity, self.logger.info)
        log_method(event_name, **log_context)
        if self.metrics is None:
            return
        self.metrics.increment_counter(
            "bioetl_observability_events_total",
            1,
            labels=payload.metric_labels,
        )

    def _record_pipeline_terminal_metrics(
        self: _CompositeLifecycleTracingHost,
        *,
        composite_name: str,
        duration_seconds: float | None,
        status: str,
    ) -> None:
        """Emit composite run duration and terminal counter metrics."""
        if self.metrics is None:
            return
        pipeline_name = self._pipeline_name(composite_name)
        if duration_seconds is not None:
            self.metrics.observe_histogram(
                "bioetl_pipeline_duration_seconds",
                duration_seconds,
                labels={
                    "pipeline": pipeline_name,
                    "stage": "pipeline",
                    "run_type": "composite",
                    "status": status,
                },
            )
        self.metrics.increment_counter(
            "bioetl_pipeline_runs_total",
            1,
            labels={
                "pipeline": pipeline_name,
                "run_type": "composite",
                "status": status,
            },
        )

    def _record_phase_duration(
        self: _CompositeLifecycleTracingHost,
        *,
        composite_name: str,
        phase_name: str,
        duration_seconds: float,
        status: str,
    ) -> None:
        """Emit composite phase duration metric."""
        if self.metrics is None:
            return
        self.metrics.observe_histogram(
            "bioetl_phase_duration_seconds",
            duration_seconds,
            labels={
                "pipeline": self._pipeline_name(composite_name),
                "phase": phase_name,
                "status": status,
            },
        )


__all__ = ["CompositeLifecycleEventMetricsMixin"]
