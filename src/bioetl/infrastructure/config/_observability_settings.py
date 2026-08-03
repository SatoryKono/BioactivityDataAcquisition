"""Observability configuration settings."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from bioetl.domain.constants import DEFAULT_DQ_QUALITY_SCORE_MIN


class ObservabilitySettings(BaseSettings):
    """Observability configuration."""

    model_config = SettingsConfigDict(frozen=True)

    metrics_enabled: bool = Field(default=True)
    """Enable metrics collection."""

    metrics_server_enabled: bool = Field(default=True)
    """Enable Prometheus metrics HTTP server. Requires metrics_enabled=True."""

    metrics_fail_fast: bool = Field(default=False)
    """If True, exit with error when metrics server fails to start."""

    metrics_retry_count: int = Field(default=3, ge=1, le=10)
    """Number of retries for transient errors when starting metrics server."""

    metrics_retry_delay: float = Field(default=1.0, ge=0.1, le=10.0)
    """Delay between retries in seconds when starting metrics server."""

    tracing_enabled: bool = Field(default=False)
    """Enable OpenTelemetry tracing."""

    allow_noop_observability_in_prod: bool = Field(default=False)
    """Allow NoOp metrics/tracing in prod without failing bootstrap validation."""

    audit_enabled: bool = Field(default=False)
    """Enable file-backed audit logging for Medallion write operations."""

    audit_base_path: Path | None = Field(default=None)
    """Optional override path for audit JSONL files."""

    # Data Quality Monitor settings
    dq_monitor_enabled: bool = Field(default=True)
    """Enable data quality monitoring. Enabled by default for all pipelines."""

    dq_baseline_window: int = Field(default=7, ge=1, le=30)
    """Number of recent runs to use for baseline calculation."""

    dq_z_score_threshold: float = Field(default=2.5, ge=1.5, le=5.0)
    """Z-score threshold for anomaly detection."""

    dq_min_baseline_samples: int = Field(default=3, ge=1, le=10)
    """Minimum samples before anomaly detection activates."""

    dq_cold_start_runs: int = Field(default=5, ge=0, le=20)
    """Skip first N runs while building baseline."""

    dq_error_rate_max: float = Field(default=0.10, ge=0.0, le=1.0)
    """Maximum allowed error rate (10% default)."""

    dq_quality_score_min: float = Field(
        default=DEFAULT_DQ_QUALITY_SCORE_MIN, ge=0.0, le=1.0
    )
    """Minimum quality score threshold (80% default)."""
