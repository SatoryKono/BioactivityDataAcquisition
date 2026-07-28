# pyright: reportUninitializedInstanceVariable=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Shared gateway and tracing helpers for the application metrics service."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.observability.span_attribute_values import (
    coerce_span_attribute_value,
)
from bioetl.application.observability.tracing_operation_helpers import traced_operation
from bioetl.domain.exceptions import BioETLError

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.ports import LoggerPort, MetricsPublisherPort, TracingPort

_METRICS_GATEWAY_ERRORS = (
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)


@dataclass(frozen=True, slots=True)
class PushResult:
    """Result of publishing metrics to an external gateway."""

    success: bool
    gateway: str
    run_label: str
    grouping_key: dict[str, str]
    error: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteResult:
    """Result of deleting metrics from an external gateway."""

    success: bool
    gateway: str
    run_label: str
    grouping_key: dict[str, str]
    error: str | None = None


class _MetricsTracingMixin:
    """Tracing attribute helpers for metrics administration flows."""

    TRACER_NAME = "bioetl.metrics_admin"

    def _build_span_attributes(
        self,
        *,
        operation: str,
        **extra: object,
    ) -> dict[str, object]:
        """Build bounded tracing attributes for operator metrics workflows."""
        return {
            "bioetl.component": "metrics_service",
            "bioetl.operation": operation,
            **extra,
        }

    @staticmethod
    def _set_result_attributes(
        span: Span,
        *,
        success: bool,
        error: str | None = None,
        attributes: Mapping[str, object] | None = None,
    ) -> None:
        """Attach bounded result attributes to the active metrics span."""
        span.set_attribute("bioetl.success", success)
        for key, value in (attributes or {}).items():
            span.set_attribute(key, coerce_span_attribute_value(value))
        if error is not None:
            span.set_attribute("error", True)
            span.set_attribute("bioetl.error", error)


class _MetricsGatewayMixin(_MetricsTracingMixin):
    """Gateway publication helpers for metrics administration flows."""

    logger: LoggerPort
    tracer: TracingPort | None
    _publisher: MetricsPublisherPort | None

    def push_to_gateway(
        self,
        *,
        gateway: str,
        run_label: str = "bioetl",
        grouping_key: dict[str, str] | None = None,
        metric_names: tuple[str, ...] | None = None,
    ) -> PushResult:
        """Publish current metrics snapshot through the explicit publisher port."""
        labels = dict(grouping_key or {})
        if self.tracer is None:
            return self._push_to_gateway_impl(
                gateway=gateway,
                run_label=run_label,
                labels=labels,
                metric_names=metric_names,
            )
        with traced_operation(
            self.tracer,
            "metrics.push_to_gateway",
            self._build_span_attributes(
                operation="push_to_gateway",
                **{
                    "bioetl.run_label": run_label,
                    "bioetl.grouping_key_count": len(labels),
                },
            ),
            tracer_name=self.TRACER_NAME,
        ) as span:
            result = self._push_to_gateway_impl(
                gateway=gateway,
                run_label=run_label,
                labels=labels,
                metric_names=metric_names,
            )
            self._set_result_attributes(
                span, success=result.success, error=result.error
            )
            return result

    def _push_to_gateway_impl(
        self,
        *,
        gateway: str,
        run_label: str,
        labels: dict[str, str],
        metric_names: tuple[str, ...] | None,
    ) -> PushResult:
        """Implement gateway publication without tracing concerns."""
        if self._publisher is None:
            error = "Metrics publisher is not configured"
            self.logger.warning(
                "Metrics gateway publication unavailable",
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
                error=error,
            )
            return PushResult(
                success=False,
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
                error=error,
            )

        try:
            success = self._publisher.push_to_gateway(
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
                metric_names=metric_names,
            )
        except _METRICS_GATEWAY_ERRORS as exc:
            error = str(exc)
            self.logger.warning(
                "Metrics gateway publication failed",
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
                error=error,
                error_type=type(exc).__name__,
            )
            return PushResult(
                success=False,
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
                error=error,
            )

        if success:
            self.logger.info(
                "Metrics gateway publication completed",
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
            )
            return PushResult(
                success=True,
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
            )

        error = "Publisher returned unsuccessful result"
        self.logger.warning(
            "Metrics gateway publication failed",
            gateway=gateway,
            run_label=run_label,
            grouping_key=labels,
            error=error,
        )
        return PushResult(
            success=False,
            gateway=gateway,
            run_label=run_label,
            grouping_key=labels,
            error=error,
        )

    def delete_from_gateway(
        self,
        *,
        gateway: str,
        run_label: str = "bioetl",
        grouping_key: dict[str, str] | None = None,
    ) -> DeleteResult:
        """Delete current metrics snapshot through the explicit publisher port."""
        labels = dict(grouping_key or {})
        if self.tracer is None:
            return self._delete_from_gateway_impl(
                gateway=gateway,
                run_label=run_label,
                labels=labels,
            )
        with traced_operation(
            self.tracer,
            "metrics.delete_from_gateway",
            self._build_span_attributes(
                operation="delete_from_gateway",
                **{
                    "bioetl.run_label": run_label,
                    "bioetl.grouping_key_count": len(labels),
                },
            ),
            tracer_name=self.TRACER_NAME,
        ) as span:
            result = self._delete_from_gateway_impl(
                gateway=gateway,
                run_label=run_label,
                labels=labels,
            )
            self._set_result_attributes(
                span, success=result.success, error=result.error
            )
            return result

    def _delete_from_gateway_impl(
        self,
        *,
        gateway: str,
        run_label: str,
        labels: dict[str, str],
    ) -> DeleteResult:
        """Implement gateway cleanup without tracing concerns."""
        if self._publisher is None:
            error = "Metrics publisher is not configured"
            self.logger.warning(
                "Metrics gateway cleanup unavailable",
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
                error=error,
            )
            return DeleteResult(
                success=False,
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
                error=error,
            )

        try:
            success = self._publisher.delete_from_gateway(
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
            )
        except _METRICS_GATEWAY_ERRORS as exc:
            error = str(exc)
            self.logger.warning(
                "Metrics gateway cleanup failed",
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
                error=error,
                error_type=type(exc).__name__,
            )
            return DeleteResult(
                success=False,
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
                error=error,
            )

        if success:
            self.logger.info(
                "Metrics gateway cleanup completed",
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
            )
            return DeleteResult(
                success=True,
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
            )

        error = "Publisher returned unsuccessful result"
        self.logger.warning(
            "Metrics gateway cleanup failed",
            gateway=gateway,
            run_label=run_label,
            grouping_key=labels,
            error=error,
        )
        return DeleteResult(
            success=False,
            gateway=gateway,
            run_label=run_label,
            grouping_key=labels,
            error=error,
        )
