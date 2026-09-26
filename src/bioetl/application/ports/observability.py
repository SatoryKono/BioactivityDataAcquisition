"""Observability settings contract for application/composition callers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ObservabilitySettingsProtocol(Protocol):
    """Typed view of metrics exposition settings used by health composition."""

    metrics_enabled: bool
    metrics_server_enabled: bool
    metrics_fail_fast: bool
    metrics_retry_count: int
    metrics_retry_delay: float
