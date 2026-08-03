"""Recording MetricsPort / TracingPort fakes for unit tests (TEST-SYS-09)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricCall:
    kind: str
    name: str
    value: float | int | None = None
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class SpanCall:
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)


class RecordingMetrics:
    """Minimal MetricsPort-compatible recorder."""

    def __init__(self) -> None:
        self.calls: list[MetricCall] = []

    def increment_counter(
        self,
        name: str,
        value: float | int = 1,
        labels: dict[str, str] | None = None,
    ) -> None:
        self.calls.append(
            MetricCall(
                kind="counter",
                name=name,
                value=value,
                labels=dict(labels or {}),
            )
        )

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        self.calls.append(
            MetricCall(
                kind="histogram",
                name=name,
                value=value,
                labels=dict(labels or {}),
            )
        )

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        self.calls.append(
            MetricCall(
                kind="gauge",
                name=name,
                value=value,
                labels=dict(labels or {}),
            )
        )

    def counter_names(self) -> list[str]:
        return [c.name for c in self.calls if c.kind == "counter"]


class RecordingTracing:
    """Minimal TracingPort-compatible recorder."""

    def __init__(self) -> None:
        self.spans: list[SpanCall] = []

    def start_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> _SpanCtx:
        self.spans.append(SpanCall(name=name, attributes=dict(attributes or {})))
        return _SpanCtx(name)


class _SpanCtx:
    def __init__(self, name: str) -> None:
        self.name = name

    def __enter__(self) -> _SpanCtx:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def set_attribute(self, key: str, value: Any) -> None:
        _ = (key, value)
        return None
