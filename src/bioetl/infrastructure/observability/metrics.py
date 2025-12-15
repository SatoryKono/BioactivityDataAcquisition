"""Prometheus metrics collection and export.

Implements REQ-OBS-002, REQ-OBS-003 from RULES.md Section 2.3.

Metrics exported:
- Pipeline execution metrics (success/failure counts, duration)
- Record processing metrics (Bronze/Silver/Gold counts)
- Error metrics (quarantine counts by error code)
- System health metrics (lock status, checkpoint age)
- Provider-specific metrics (API calls, rate limit hits, circuit breaker state)
- Data quality metrics (validation errors, schema drift)

Usage:
    # In pipeline code
    collector = MetricsCollector(pipeline_name="chembl_activity")
    collector.record_processed(layer="bronze", count=1000)
    collector.record_error(error_code="VALIDATION_ERROR")

    # In main application startup
    exporter = PrometheusExporter(port=9090)
    exporter.start()
"""

from __future__ import annotations

import logging
import threading
from enum import Enum
from typing import TYPE_CHECKING

from prometheus_client import (
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    Summary,
    start_http_server,
)

if TYPE_CHECKING:
    from prometheus_client.registry import CollectorRegistry

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Metric types supported by Prometheus."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class MetricsCollector:
    """Collects and exposes application metrics for Prometheus.

    Thread-safe metrics collector that aggregates metrics from multiple
    pipeline runs and system components.

    Attributes:
        pipeline_name: Name of the pipeline (e.g., "chembl_activity")
        registry: Prometheus registry (default: REGISTRY)
    """

    def __init__(
        self,
        pipeline_name: str,
        registry: CollectorRegistry | None = None,
    ) -> None:
        """Initialize metrics collector.

        Args:
            pipeline_name: Pipeline identifier for metric labels
            registry: Prometheus registry (default: global REGISTRY)
        """
        self.pipeline_name = pipeline_name
        self.registry = registry or REGISTRY
        self._lock = threading.Lock()

        # Pipeline execution metrics
        self.pipeline_runs_total = Counter(
            "bioetl_pipeline_runs_total",
            "Total number of pipeline runs",
            ["pipeline", "run_type", "status"],
            registry=self.registry,
        )

        self.pipeline_duration_seconds = Histogram(
            "bioetl_pipeline_duration_seconds",
            "Pipeline execution duration in seconds",
            ["pipeline", "run_type"],
            buckets=[60, 300, 900, 1800, 3600, 7200, 14400],  # 1m to 4h
            registry=self.registry,
        )

        # Record processing metrics
        self.records_processed_total = Counter(
            "bioetl_records_processed_total",
            "Total number of records processed",
            ["pipeline", "layer", "status"],
            registry=self.registry,
        )

        self.records_in_progress = Gauge(
            "bioetl_records_in_progress",
            "Number of records currently being processed",
            ["pipeline", "layer"],
            registry=self.registry,
        )

        # Error metrics
        self.errors_total = Counter(
            "bioetl_errors_total",
            "Total number of errors",
            ["pipeline", "error_code", "layer"],
            registry=self.registry,
        )

        self.quarantine_records_total = Counter(
            "bioetl_quarantine_records_total",
            "Total number of records quarantined",
            ["pipeline", "error_code"],
            registry=self.registry,
        )

        # Lock and checkpoint metrics
        self.lock_acquisitions_total = Counter(
            "bioetl_lock_acquisitions_total",
            "Total number of lock acquisition attempts",
            ["pipeline", "status"],
            registry=self.registry,
        )

        self.lock_held_seconds = Gauge(
            "bioetl_lock_held_seconds",
            "Duration lock has been held (0 if not held)",
            ["pipeline"],
            registry=self.registry,
        )

        self.checkpoint_age_seconds = Gauge(
            "bioetl_checkpoint_age_seconds",
            "Time since last checkpoint save",
            ["pipeline"],
            registry=self.registry,
        )

        # Provider API metrics
        self.api_requests_total = Counter(
            "bioetl_api_requests_total",
            "Total number of API requests to providers",
            ["provider", "endpoint", "status"],
            registry=self.registry,
        )

        self.api_request_duration_seconds = Summary(
            "bioetl_api_request_duration_seconds",
            "API request duration in seconds",
            ["provider", "endpoint"],
            registry=self.registry,
        )

        self.rate_limit_hits_total = Counter(
            "bioetl_rate_limit_hits_total",
            "Number of times rate limit was hit",
            ["provider"],
            registry=self.registry,
        )

        self.circuit_breaker_state = Gauge(
            "bioetl_circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=open, 2=half_open)",
            ["provider"],
            registry=self.registry,
        )

        # Data quality metrics
        self.validation_errors_total = Counter(
            "bioetl_validation_errors_total",
            "Total number of validation errors",
            ["pipeline", "schema", "error_type"],
            registry=self.registry,
        )

        self.schema_drift_detected_total = Counter(
            "bioetl_schema_drift_detected_total",
            "Number of times schema drift was detected",
            ["pipeline", "table", "drift_type"],
            registry=self.registry,
        )

        self.data_quality_score = Gauge(
            "bioetl_data_quality_score",
            "Overall data quality score (0-1)",
            ["pipeline", "layer"],
            registry=self.registry,
        )

    def record_pipeline_run(
        self,
        run_type: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        """Record pipeline run completion.

        Args:
            run_type: Type of run (incremental, backfill, rebuild)
            status: Run status (success, failure)
            duration_seconds: Execution duration in seconds
        """
        with self._lock:
            self.pipeline_runs_total.labels(
                pipeline=self.pipeline_name,
                run_type=run_type,
                status=status,
            ).inc()

            self.pipeline_duration_seconds.labels(
                pipeline=self.pipeline_name,
                run_type=run_type,
            ).observe(duration_seconds)

    def record_processed(
        self,
        layer: str,
        count: int = 1,
        status: str = "success",
    ) -> None:
        """Record processed records.

        Args:
            layer: Data layer (bronze, silver, gold)
            count: Number of records processed
            status: Processing status (success, failure)
        """
        with self._lock:
            self.records_processed_total.labels(
                pipeline=self.pipeline_name,
                layer=layer,
                status=status,
            ).inc(count)

    def update_in_progress(self, layer: str, count: int) -> None:
        """Update in-progress record count.

        Args:
            layer: Data layer (bronze, silver, gold)
            count: Current number of records in progress
        """
        with self._lock:
            self.records_in_progress.labels(
                pipeline=self.pipeline_name,
                layer=layer,
            ).set(count)

    def record_error(
        self,
        error_code: str,
        layer: str = "unknown",
    ) -> None:
        """Record an error occurrence.

        Args:
            error_code: Error code (e.g., VALIDATION_ERROR)
            layer: Data layer where error occurred
        """
        with self._lock:
            self.errors_total.labels(
                pipeline=self.pipeline_name,
                error_code=error_code,
                layer=layer,
            ).inc()

    def record_quarantine(self, error_code: str) -> None:
        """Record a quarantined record.

        Args:
            error_code: Reason for quarantine
        """
        with self._lock:
            self.quarantine_records_total.labels(
                pipeline=self.pipeline_name,
                error_code=error_code,
            ).inc()

    def record_lock_acquisition(self, success: bool) -> None:
        """Record lock acquisition attempt.

        Args:
            success: Whether lock was acquired
        """
        status = "success" if success else "failure"
        with self._lock:
            self.lock_acquisitions_total.labels(
                pipeline=self.pipeline_name,
                status=status,
            ).inc()

    def update_lock_duration(self, seconds: float) -> None:
        """Update lock held duration.

        Args:
            seconds: Duration lock has been held (0 if released)
        """
        with self._lock:
            self.lock_held_seconds.labels(
                pipeline=self.pipeline_name,
            ).set(seconds)

    def update_checkpoint_age(self, seconds: float) -> None:
        """Update checkpoint age.

        Args:
            seconds: Time since last checkpoint save
        """
        with self._lock:
            self.checkpoint_age_seconds.labels(
                pipeline=self.pipeline_name,
            ).set(seconds)

    def record_api_request(
        self,
        provider: str,
        endpoint: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        """Record API request to provider.

        Args:
            provider: Provider name (chembl, pubchem, uniprot)
            endpoint: API endpoint
            status: HTTP status code or "error"
            duration_seconds: Request duration
        """
        with self._lock:
            self.api_requests_total.labels(
                provider=provider,
                endpoint=endpoint,
                status=status,
            ).inc()

            self.api_request_duration_seconds.labels(
                provider=provider,
                endpoint=endpoint,
            ).observe(duration_seconds)

    def record_rate_limit_hit(self, provider: str) -> None:
        """Record rate limit hit.

        Args:
            provider: Provider name
        """
        with self._lock:
            self.rate_limit_hits_total.labels(
                provider=provider,
            ).inc()

    def update_circuit_breaker_state(
        self,
        provider: str,
        state: str,
    ) -> None:
        """Update circuit breaker state.

        Args:
            provider: Provider name
            state: Circuit breaker state (CLOSED, OPEN, HALF_OPEN)
        """
        state_value = {"CLOSED": 0, "OPEN": 1, "HALF_OPEN": 2}.get(state, -1)
        with self._lock:
            self.circuit_breaker_state.labels(
                provider=provider,
            ).set(state_value)

    def record_validation_error(
        self,
        schema: str,
        error_type: str,
    ) -> None:
        """Record validation error.

        Args:
            schema: Schema name
            error_type: Type of validation error
        """
        with self._lock:
            self.validation_errors_total.labels(
                pipeline=self.pipeline_name,
                schema=schema,
                error_type=error_type,
            ).inc()

    def record_schema_drift(
        self,
        table: str,
        drift_type: str,
    ) -> None:
        """Record schema drift detection.

        Args:
            table: Table name
            drift_type: Type of drift (new_column, removed_column, type_change)
        """
        with self._lock:
            self.schema_drift_detected_total.labels(
                pipeline=self.pipeline_name,
                table=table,
                drift_type=drift_type,
            ).inc()

    def update_data_quality_score(
        self,
        layer: str,
        score: float,
    ) -> None:
        """Update data quality score.

        Args:
            layer: Data layer (bronze, silver, gold)
            score: Quality score between 0 and 1
        """
        if not 0 <= score <= 1:
            raise ValueError(f"Quality score must be between 0 and 1, got {score}")

        with self._lock:
            self.data_quality_score.labels(
                pipeline=self.pipeline_name,
                layer=layer,
            ).set(score)


class PrometheusExporter:
    """HTTP server for Prometheus metrics export.

    Starts an HTTP server that exposes metrics at /metrics endpoint.

    Usage:
        exporter = PrometheusExporter(port=9090)
        exporter.start()
        # Metrics available at http://localhost:9090/metrics
        exporter.stop()
    """

    def __init__(
        self,
        port: int = 9090,
        addr: str = "0.0.0.0",
        registry: CollectorRegistry | None = None,
    ) -> None:
        """Initialize Prometheus exporter.

        Args:
            port: HTTP port for metrics endpoint
            addr: Bind address (default: 0.0.0.0)
            registry: Prometheus registry (default: REGISTRY)
        """
        self.port = port
        self.addr = addr
        self.registry = registry or REGISTRY
        self._server_thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        """Start HTTP server for metrics export.

        Raises:
            RuntimeError: If server is already running
        """
        if self._running:
            raise RuntimeError("Prometheus exporter already running")

        logger.info(f"Starting Prometheus metrics server on {self.addr}:{self.port}")

        # Start HTTP server in separate thread
        start_http_server(
            port=self.port,
            addr=self.addr,
            registry=self.registry,
        )

        self._running = True
        logger.info(
            f"Prometheus metrics available at http://{self.addr}:{self.port}/metrics"
        )

    def stop(self) -> None:
        """Stop metrics server.

        Note: prometheus_client doesn't provide graceful shutdown,
        so this just marks the exporter as stopped.
        """
        if not self._running:
            return

        self._running = False
        logger.info("Prometheus exporter stopped")

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running
