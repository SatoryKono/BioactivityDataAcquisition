"""Manifest-to-ledger referential-integrity metric tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.application.services.control_plane.manifest.integrity_metrics import (
    MANIFEST_LEDGER_INTEGRITY_METRIC,
    ControlPlaneIntegrityMetricsService,
    manifest_expects_ledger,
)
from bioetl.domain.control_plane import (
    RunLedgerEntry,
    RunManifest,
)
from bioetl.domain.control_plane.run_ledger import MANIFEST_CREATED_EVENT
from bioetl.domain.types import RunID
from tests.fakes.metrics_fake import RecordingMetrics
from tests.helpers.control_plane import (
    InMemoryRunLedgerStore,
    InMemoryRunManifestStore,
)
from tests.helpers.deterministic_ids import deterministic_uuid
from tests.unit.application.services.run_manifest_test_support import (
    RunManifestOverrides,
    make_run_manifest,
)

pytestmark = pytest.mark.unit

_OCCURRED_AT = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)


def _entry(
    manifest: RunManifest,
    event_type: str,
    entry_id: str,
    *,
    manifest_id: str | None = None,
    run_id: RunID | None = None,
) -> RunLedgerEntry:
    return RunLedgerEntry(
        entry_id=entry_id,
        manifest_id=manifest_id or manifest.manifest_id,
        run_id=run_id or manifest.run_id,
        event_type=event_type,
        occurred_at=_OCCURRED_AT,
    )


def _service(
    manifests: InMemoryRunManifestStore,
    ledger: InMemoryRunLedgerStore,
    metrics: RecordingMetrics,
) -> ControlPlaneIntegrityMetricsService:
    return ControlPlaneIntegrityMetricsService(
        manifest_port=manifests,
        ledger_port=ledger,
        metrics=metrics,  # type: ignore[arg-type]
    )


def test_refresh_publishes_complementary_scope_ratios() -> None:
    manifests = InMemoryRunManifestStore()
    ledger = InMemoryRunLedgerStore()
    consistent = make_run_manifest(manifest_id="manifest-consistent")
    inconsistent = make_run_manifest(manifest_id="manifest-inconsistent")
    manifests.save(consistent)
    manifests.save(inconsistent)
    ledger.append(
        _entry(consistent, MANIFEST_CREATED_EVENT, "entry-manifest-created")
    )
    metrics = RecordingMetrics()

    result = _service(manifests, ledger, metrics).refresh()

    assert len(result) == 1
    assert result[0].consistent == 1
    assert result[0].inconsistent == 1
    assert result[0].denominator == 2
    assert result[0].consistent_ratio == 0.5
    assert result[0].inconsistent_ratio == 0.5
    assert [
        (call.value, call.labels["integrity_type"])
        for call in metrics.calls
        if call.name == MANIFEST_LEDGER_INTEGRITY_METRIC
    ] == [(0.5, "consistent"), (0.5, "inconsistent")]


@pytest.mark.parametrize(
    "launch_context",
    [
        {"run_ledger_enabled": False},
        {"ledger_enabled": "false"},
    ],
)
def test_explicitly_disabled_ledger_is_excluded_from_denominator(
    launch_context: dict[str, object],
) -> None:
    manifest = make_run_manifest(
        overrides=RunManifestOverrides(launch_context=launch_context)
    )

    assert manifest_expects_ledger(manifest) is False


def test_absent_ledger_flag_defaults_to_expected() -> None:
    assert manifest_expects_ledger(make_run_manifest()) is True


@pytest.mark.parametrize(
    "events",
    [
        ("artifact_published", MANIFEST_CREATED_EVENT),
        (MANIFEST_CREATED_EVENT, MANIFEST_CREATED_EVENT),
    ],
)
def test_manifest_created_must_be_first_and_unique(events: tuple[str, ...]) -> None:
    manifests = InMemoryRunManifestStore()
    ledger = InMemoryRunLedgerStore()
    manifest = make_run_manifest()
    manifests.save(manifest)
    for index, event_type in enumerate(events):
        ledger.append(_entry(manifest, event_type, f"entry-{index}"))

    result = _service(manifests, ledger, RecordingMetrics()).refresh()

    assert result[0].consistent == 0
    assert result[0].inconsistent == 1


def test_every_ledger_entry_must_match_manifest_and_run_identity() -> None:
    manifests = InMemoryRunManifestStore()
    ledger = InMemoryRunLedgerStore()
    manifest = make_run_manifest()
    manifests.save(manifest)
    ledger.append(_entry(manifest, MANIFEST_CREATED_EVENT, "entry-1"))
    ledger.append(
        _entry(
            manifest,
            "run_completed",
            "entry-2",
            run_id=RunID(deterministic_uuid("integrity:wrong-run")),
        )
    )

    result = _service(manifests, ledger, RecordingMetrics()).refresh()

    assert result[0].consistent == 0
    assert result[0].inconsistent == 1


def test_zero_denominator_clears_stale_series_without_claiming_healthy() -> None:
    manifests = InMemoryRunManifestStore()
    ledger = InMemoryRunLedgerStore()
    manifest = make_run_manifest()
    manifests.save(manifest)
    ledger.append(_entry(manifest, MANIFEST_CREATED_EVENT, "entry-1"))
    metrics = RecordingMetrics()
    service = _service(manifests, ledger, metrics)
    service.refresh()
    manifests.items.clear()

    result = service.refresh()

    assert result == ()
    assert [
        (call.value, call.labels["integrity_type"])
        for call in metrics.calls[-2:]
    ] == [(0.0, "consistent"), (0.0, "inconsistent")]
