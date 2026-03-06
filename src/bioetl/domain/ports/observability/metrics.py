"""Metrics protocol ports."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MetricsPort(Protocol):
    """Port for metrics collection."""

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None: ...

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: dict[str, str],
    ) -> None: ...

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None: ...

    def inc_quarantine_records(
        self,
        pipeline: str,
        reason: str,
        count: int = 1,
    ) -> None: ...

    def inc_dq_validation_failures(
        self,
        pipeline: str,
        stage: str,
        severity: str,
        count: int = 1,
    ) -> None: ...

    def close(self) -> None: ...


@runtime_checkable
class ExecutorMetricsPort(Protocol):
    """Protocol for executors providing batch metrics."""

    records_fetched: int
    records_bronze: int
    records_silver: int
    records_gold: int
    records_quarantined: int


@runtime_checkable
class MetricsServerPort(Protocol):
    """Protocol for metrics server operations."""

    def start(
        self,
        port: int,
        *,
        fail_fast: bool = False,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ) -> bool: ...

    def is_running(self) -> bool: ...

    def reset(self) -> None: ...
