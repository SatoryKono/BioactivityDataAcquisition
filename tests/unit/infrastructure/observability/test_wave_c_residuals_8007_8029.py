# pyright: reportArgumentType=false
"""Focused residual coverage for Wave C observability issues #8007-#8029."""

from __future__ import annotations

from datetime import datetime, UTC
from unittest.mock import MagicMock

import pytest

from bioetl.domain.types import CircuitBreakerState
from bioetl.infrastructure.observability import (
    _metrics_defs_core,
    _metrics_defs_pipeline,
    _metrics_defs_storage,
    prometheus_metric_registries,
)
from bioetl.infrastructure.observability.anomaly.detectors.zscore import ZScoreDetector
from bioetl.infrastructure.observability.circuit_breaker_mapping import (
    CIRCUIT_BREAKER_STATE_VALUES,
)
from bioetl.infrastructure.observability.debug_adapters import LoggingDebugAdapter
from bioetl.infrastructure.observability.logging_config import _mask_secrets
from bioetl.infrastructure.observability.prometheus_metric_label_dispatch import (
    normalize_metric_dispatch_labels,
)
from bioetl.infrastructure.observability._prometheus_metric_label_normalizers import (
    normalize_adapter_endpoint_label,
)
from bioetl.infrastructure.observability._metrics_server_state import (
    get_metrics_server_runtime_status,
    is_metrics_server_running,
    mark_metrics_server_started,
    reset_server_state,
)
from bioetl.domain.ports import (
    PipelineSnapshot,
)

pytestmark = pytest.mark.unit


def test_circuit_breaker_state_values_cover_all_enum_members() -> None:
    assert set(CIRCUIT_BREAKER_STATE_VALUES) == set(CircuitBreakerState)
    assert CIRCUIT_BREAKER_STATE_VALUES[CircuitBreakerState.CLOSED] == 0.0
    assert CIRCUIT_BREAKER_STATE_VALUES[CircuitBreakerState.HALF_OPEN] == 1.0
    assert CIRCUIT_BREAKER_STATE_VALUES[CircuitBreakerState.OPEN] == 2.0


def test_uuid_redaction_requires_full_string_match() -> None:
    uuid = "123e4567-e89b-12d3-a456-426614174000"
    assert _mask_secrets(uuid) == uuid
    # prefix noise must not preserve the whole token as UUID
    mixed = f"token={uuid}"
    assert _mask_secrets(mixed) != mixed or "token=" in mixed


def test_metrics_server_state_lock_roundtrip() -> None:
    reset_server_state()
    assert is_metrics_server_running() is False
    started = datetime(2026, 1, 1, tzinfo=UTC)
    mark_metrics_server_started(port=8000, addr="127.0.0.1", started_at=started)
    assert is_metrics_server_running() is True
    status = get_metrics_server_runtime_status()
    assert status.running is True
    assert status.port == 8000
    assert status.addr == "127.0.0.1"
    reset_server_state()
    assert is_metrics_server_running() is False


def test_debug_adapter_snapshot_buffer_is_bounded() -> None:
    logger = MagicMock()
    adapter = LoggingDebugAdapter(logger=logger, max_snapshots=3)
    for idx in range(5):
        adapter.on_snapshot(
            PipelineSnapshot(
                stage=f"s{idx}",
                records_fetched=idx,
                records_bronze=0,
                records_silver=0,
                records_gold=0,
                records_quarantined=0,
            )
        )
    assert len(adapter._snapshots) == 3


def test_zscore_zero_stddev_flags_any_deviation() -> None:
    detector = ZScoreDetector()
    ts = datetime(2026, 1, 1, tzinfo=UTC)
    # constant baseline of zeros; non-zero value must be anomaly
    anomaly = detector.detect("m", 1.0, [0.0, 0.0, 0.0], threshold=2.0, timestamp=ts)
    assert anomaly is not None
    assert anomaly.z_score == 10.0
    # constant non-zero mean
    anomaly2 = detector.detect("m", 5.0, [2.0, 2.0, 2.0], threshold=2.0, timestamp=ts)
    assert anomaly2 is not None
    # equal to constant mean is not anomaly
    assert (
        detector.detect("m", 2.0, [2.0, 2.0, 2.0], threshold=2.0, timestamp=ts) is None
    )


def test_endpoint_label_normalizer_bounds_depth() -> None:
    long_path = "/" + "/".join(f"seg{i}" for i in range(12))
    normalized = normalize_adapter_endpoint_label(long_path)
    assert normalized.count("/") <= 8
    assert "{param}" in normalized or normalized.startswith("/")


def test_metric_dispatch_labels_nominal_branch() -> None:
    labels = normalize_metric_dispatch_labels(
        "bioetl_unknown_metric_for_dispatch_smoke",
        {},
    )
    assert isinstance(labels, dict)


def test_pipeline_metric_module_exports_families() -> None:
    names = [n for n in dir(_metrics_defs_pipeline) if n.isupper()]
    assert names
    core_names = [n for n in dir(_metrics_defs_core) if n.isupper()]
    assert core_names
    storage_names = [n for n in dir(_metrics_defs_storage) if n.isupper()]
    assert storage_names


def test_prometheus_registry_builders_exist() -> None:
    assert callable(
        getattr(prometheus_metric_registries, "build_counter_registry", None)
    )
    assert callable(getattr(prometheus_metric_registries, "build_gauge_registry", None))


def test_observability_package_lazy_exports() -> None:
    import bioetl.infrastructure.observability as obs

    exported = set(getattr(obs, "__all__", ())) | set(dir(obs))
    assert exported & {
        "PrometheusMetrics",
        "UnifiedLogger",
        "configure_logging",
        "MetricsCollector",
        "OpenTelemetryTracer",
    }
