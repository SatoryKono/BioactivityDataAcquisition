"""Unit tests for persisted provider-health CURRENT evidence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from bioetl.infrastructure.control_plane.provider_health_evidence import (
    rehydrate_provider_health_evidence,
)
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.control_plane.file_provider_health_evidence import (
    FileProviderHealthEvidenceStore,
    ProviderHealthEvidenceRecord,
)
from tests.fakes.metrics_fake import RecordingMetrics

pytestmark = pytest.mark.unit


def _gauge_names(metrics: RecordingMetrics) -> list[str]:
    return [call.name for call in metrics.calls if call.kind == "gauge"]


def test_persist_and_rehydrate_fresh_status(tmp_path: Path) -> None:
    store = FileProviderHealthEvidenceStore(base_path=tmp_path)
    now = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
    store.persist(
        ProviderHealthEvidenceRecord(
            provider="chembl",
            status=HealthStatus.HEALTHY.to_metric_value(),
            observed_at=now.isoformat(),
            endpoint="/status",
        )
    )
    metrics = RecordingMetrics()
    published = rehydrate_provider_health_evidence(metrics, store, now=now)
    assert published == 1
    names = _gauge_names(metrics)
    assert "bioetl_provider_health_status" in names
    assert "bioetl_provider_observed_universe" in names
    assert metrics.counter_names() == []


def test_stale_evidence_does_not_publish_health_status(tmp_path: Path) -> None:
    store = FileProviderHealthEvidenceStore(base_path=tmp_path)
    observed = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
    store.persist(
        ProviderHealthEvidenceRecord(
            provider="chembl",
            status=2,
            observed_at=observed.isoformat(),
            endpoint="/status",
        )
    )
    metrics = RecordingMetrics()
    rehydrate_provider_health_evidence(
        metrics,
        store,
        now=observed + timedelta(minutes=20),
    )
    names = _gauge_names(metrics)
    assert "bioetl_provider_observed_universe" in names
    assert "bioetl_provider_health_status" not in names

def test_persisting_monitor_writes_compact_evidence(tmp_path: Path) -> None:
    from unittest.mock import MagicMock

    from bioetl.infrastructure.control_plane.provider_health_evidence import (
        PersistingProviderHealthMonitor,
    )
    from bioetl.domain.ports.health_check import HealthCheckResult

    inner = MagicMock()
    inner.update_from_health_check_result.return_value = HealthStatus.HEALTHY
    store = FileProviderHealthEvidenceStore(base_path=tmp_path)
    monitor = PersistingProviderHealthMonitor(inner=inner, store=store)
    now = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
    monitor.update_from_health_check_result(
        HealthCheckResult(
            status=HealthStatus.HEALTHY,
            latency_ms=12.0,
            provider="chembl",
            endpoint="/status",
            checked_at=now,
        )
    )
    loaded = store.load("chembl")
    assert loaded is not None
    assert loaded.status == HealthStatus.HEALTHY.to_metric_value()
    assert loaded.endpoint == "/status"

