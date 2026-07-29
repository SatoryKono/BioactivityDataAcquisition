# Host attrs/methods provided by concrete composition (PD2 W1).
"""Shared event emission helpers for pipeline observer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import bioetl.application.observability.observer_contract as observer_contract

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort


class _ObserverEventMixin:
    """Encapsulates contract-aware log and metric emission."""

    _logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD6)
    _metrics: MetricsPort = cast(Any, None)  # Any: host attr default (PD6)
    provider_name: str = cast(Any, None)  # Any: host attr default (PD6)
    pipeline_name: str = cast(Any, None)  # Any: host attr default (PD6)
    run_id: str = cast(Any, None)  # Any: host attr default (PD6)
    manifest_id: str | None = cast(Any, None)  # Any: host attr default (PD6)
    entity: str | None = cast(Any, None)  # Any: host attr default (PD6)
    run_type: str | None = cast(Any, None)  # Any: host attr default (PD6)
    effective_config_hash: str | None = cast(Any, None)  # Any: host attr default (PD6)
    contract_ref: str | None = cast(Any, None)  # Any: host attr default (PD6)
    contract_version: str | None = cast(Any, None)  # Any: host attr default (PD6)
    composite_run_id: str | None = cast(Any, None)  # Any: host attr default (PD6)

    @staticmethod
    def _normalize_severity(level: str) -> str:
        """Normalize severity label for logs and metrics."""
        normalized = level.strip().lower()
        if normalized in {"debug", "info", "warning", "error"}:
            return normalized
        return "info"

    @staticmethod
    def _normalize_metric_label(value: str) -> str:
        """Normalize metric label value to bounded token format."""
        normalized = (
            value.strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
            .replace(".", "_")
            .replace("/", "_")
            .replace(":", "_")
        )
        return normalized or "none"

    def _emit_contract_event(
        self,
        event_name: str,
        *,
        severity: str,
        **context: Any,  # Any: structlog-compatible context kwargs
    ) -> None:
        """Validate contract once and emit log+metric payloads."""
        payload = observer_contract.build_observability_contract_payload(
            event_name=event_name,
            context=context,
            default_provider=self.provider_name,
            default_pipeline=self.pipeline_name,
            default_run_id=self.run_id,
            default_severity=severity,
            correlation_defaults=self._build_correlation_defaults(),
        )
        self._log_event(event_name, severity=severity, context=payload.context)
        self._emit_observability_event_metric(payload.metric_labels)

    def _build_correlation_defaults(self) -> dict[str, object]:
        """Build optional correlation defaults for canonical observability context."""
        defaults: dict[str, object] = {}
        for key in (
            "manifest_id",
            "entity",
            "run_type",
            "effective_config_hash",
            "contract_ref",
            "contract_version",
            "composite_run_id",
        ):
            value = getattr(self, key, None)
            if value is not None:
                defaults[key] = value
        return defaults

    def _log_event(
        self,
        event_name: str,
        *,
        severity: str,
        context: dict[str, object],
    ) -> None:
        """Emit log entry without duplicating structlog reserved ``event`` arg."""
        log_context = dict(context)
        log_context.pop("event", None)
        log_method = getattr(self._logger, severity, self._logger.info)
        log_method(event_name, **log_context)

    def _emit_observability_event_metric(
        self,
        labels: dict[str, str],
    ) -> None:
        """Emit unified observability event metric with normalized labels."""
        self._metrics.increment_counter(
            "bioetl_observability_events_total",
            1,
            labels={
                "event": self._normalize_metric_label(labels["event"]),
                "provider": self._normalize_metric_label(labels["provider"]),
                "pipeline": self._normalize_metric_label(labels["pipeline"]),
                "severity": self._normalize_metric_label(labels["severity"]),
                "error_type": self._normalize_metric_label(labels["error_type"]),
            },
        )


__all__ = ["_ObserverEventMixin"]
