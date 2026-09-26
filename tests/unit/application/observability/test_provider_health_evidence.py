"""Unit tests for persisted provider-health CURRENT evidence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import pytest

from bioetl.domain.types import HealthStatus
from tests.fakes.metrics_fake import RecordingMetrics

pytestmark = pytest.mark.unit


def _provider_health_infra():
    from bioetl.infrastructure.control_plane.file_provider_health_evidence import (
        FileProviderHealthEvidenceStore,
        ProviderHealthEvidenceRecord,
    )
    from bioetl.infrastructure.control_plane.provider_health_evidence import (
        rehydrate_provider_health_evidence,
    )

    return (
        FileProviderHealthEvidenceStore,
        ProviderHealthEvidenceRecord,
        rehydrate_provider_health_evidence,
    )


def _gauge_names(metrics: RecordingMetrics) -> list[str]:
    return [call.name for call in metrics.calls if call.kind == "gauge"]


def test_persist_and_rehydrate_fresh_status(tmp_path: Path) -> None:
    (
        FileProviderHealthEvidenceStore,
        ProviderHealthEvidenceRecord,
        rehydrate_provider_health_evidence,
    ) = _provider_health_infra()
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


@pytest.mark.parametrize("status", [0, 1, 2])
def test_old_evidence_publishes_last_health_status(tmp_path: Path, status: int) -> None:
    (
        FileProviderHealthEvidenceStore,
        ProviderHealthEvidenceRecord,
        rehydrate_provider_health_evidence,
    ) = _provider_health_infra()
    store = FileProviderHealthEvidenceStore(base_path=tmp_path)
    observed = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
    store.persist(
        ProviderHealthEvidenceRecord(
            provider="chembl",
            status=status,
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
    assert "bioetl_provider_health_status" in names
    assert [
        c.value for c in metrics.calls if c.name == "bioetl_provider_health_status"
    ] == [status]


@pytest.mark.parametrize(
    "observed", ["invalid", "1970-01-01T00:00:00+00:00", "2099-01-01T00:00:00+00:00"]
)
def test_invalid_timestamp_never_restores_health(tmp_path: Path, observed: str) -> None:
    store_type, record_type, rehydrate = _provider_health_infra()
    store = store_type(base_path=tmp_path)
    store.persist(
        record_type(
            provider="chembl", status=2, observed_at=observed, endpoint="/status"
        )
    )
    metrics = RecordingMetrics()
    rehydrate(metrics, store, now=datetime(2026, 9, 21, tzinfo=UTC))
    assert "bioetl_provider_health_status" not in _gauge_names(metrics)


@pytest.mark.parametrize("contents", [None, "{broken", "[]"])
def test_missing_or_corrupt_store_never_publishes_health(
    tmp_path: Path, contents: str | None
) -> None:
    store_type, _, rehydrate = _provider_health_infra()
    store = store_type(base_path=tmp_path)
    if contents is not None:
        store.path_for("chembl").write_text(contents, encoding="utf-8")
    metrics = RecordingMetrics()
    assert rehydrate(metrics, store, now=datetime(2026, 9, 21, tzinfo=UTC)) == 0
    assert metrics.calls == []


@pytest.mark.parametrize(
    "field,value",
    [("schema_version", "future_schema"), ("schema_version", None), ("status", True)],
)
def test_invalid_record_contract_never_publishes_health(
    tmp_path: Path, field: str, value: object
) -> None:
    store_type, record_type, rehydrate = _provider_health_infra()
    store = store_type(base_path=tmp_path)
    payload = record_type(
        provider="chembl",
        status=2,
        observed_at="2026-08-19T12:00:00+00:00",
        endpoint="/status",
    ).to_dict()
    payload[field] = value
    store.path_for("chembl").write_text(json.dumps(payload), encoding="utf-8")
    metrics = RecordingMetrics()
    assert rehydrate(metrics, store, now=datetime(2026, 9, 21, tzinfo=UTC)) == 0
    assert metrics.calls == []


def test_new_observation_replaces_restored_status_and_keeps_real_time(
    tmp_path: Path,
) -> None:
    store_type, record_type, rehydrate = _provider_health_infra()
    store = store_type(base_path=tmp_path)
    now = datetime(2026, 9, 21, tzinfo=UTC)
    for status, observed in ((0, now - timedelta(days=30)), (2, now)):
        store.persist(
            record_type(
                provider="chembl",
                status=status,
                observed_at=observed.isoformat(),
                endpoint="/status",
            )
        )
        metrics = RecordingMetrics()
        assert rehydrate(metrics, store, now=now) == 1
        assert [
            c.value for c in metrics.calls if c.name == "bioetl_provider_health_status"
        ] == [status]
        assert [
            c.value
            for c in metrics.calls
            if c.name == "bioetl_provider_health_observed_timestamp_seconds"
        ] == [observed.timestamp()]
        assert metrics.counter_names() == []


def test_persisting_monitor_writes_compact_evidence(tmp_path: Path) -> None:
    from unittest.mock import MagicMock

    from bioetl.infrastructure.control_plane.provider_health_evidence import (
        PersistingProviderHealthMonitor,
    )
    from bioetl.domain.ports.health_check import HealthCheckResult

    inner = MagicMock()
    inner.update_from_health_check_result.return_value = HealthStatus.HEALTHY
    (
        FileProviderHealthEvidenceStore,
        ProviderHealthEvidenceRecord,
        rehydrate_provider_health_evidence,
    ) = _provider_health_infra()
    store = FileProviderHealthEvidenceStore(base_path=tmp_path)
    from bioetl.infrastructure.time import SystemClock

    monitor = PersistingProviderHealthMonitor(
        inner=inner, store=store, clock=SystemClock()
    )
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
