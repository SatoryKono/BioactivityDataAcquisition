"""Replay duplicate/overwrite risk classification and emission tests."""

from __future__ import annotations

from dataclasses import replace

import pytest

from bioetl.application.observability.replay_write_risk import (
    REPLAY_WRITE_RISK_METRIC,
    ReplayWriteRiskClassification,
    assess_replay_write_risks,
    emit_replay_write_risk_metrics,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.types import RunType
from tests.fakes.metrics_fake import RecordingMetrics
from tests.unit.application.services.run_manifest_test_support import (
    RunManifestOverrides,
    make_run_manifest,
)

pytestmark = pytest.mark.unit


def _replay_manifest(
    *,
    run_type: RunType = RunType.INCREMENTAL,
    launch_context: dict[str, object] | None = None,
    resolved_config: dict[str, object] | None = None,
) -> RunManifest:
    manifest = make_run_manifest(
        run_type=run_type,
        overrides=RunManifestOverrides(
            launch_context=launch_context or {},
            resolved_config=resolved_config or {},
        ),
    )
    return replace(manifest, replay_of_manifest_id="manifest-parent")


def test_non_replay_manifest_has_no_write_risk_but_initializes_both_series() -> None:
    manifest = make_run_manifest(
        overrides=RunManifestOverrides(
            resolved_config={
                "pipeline": {
                    "sink": {
                        "silver": {"enabled": True, "mode": "append"},
                        "gold": {"enabled": True, "mode": "overwrite"},
                    }
                }
            }
        )
    )
    metrics = RecordingMetrics()

    emit_replay_write_risk_metrics(metrics, manifest)  # type: ignore[arg-type]

    assert assess_replay_write_risks(manifest) == frozenset()
    assert [
        (call.value, call.labels)
        for call in metrics.calls
        if call.name == REPLAY_WRITE_RISK_METRIC
    ] == [
        (
            0,
            {
                "pipeline": "chembl_activity",
                "run_type": "incremental",
                "risk_type": "duplicate",
            },
        ),
        (
            0,
            {
                "pipeline": "chembl_activity",
                "run_type": "incremental",
                "risk_type": "overwrite",
            },
        ),
    ]


def test_replay_append_and_destructive_modes_emit_both_bounded_risks() -> None:
    manifest = _replay_manifest(
        resolved_config={
            "pipeline": {
                "sink": {
                    "silver": {"enabled": True, "mode": "append"},
                    "gold": {"enabled": True, "mode": "overwrite"},
                }
            }
        }
    )

    assert assess_replay_write_risks(manifest) == frozenset(
        {
            ReplayWriteRiskClassification.DUPLICATE,
            ReplayWriteRiskClassification.OVERWRITE,
        }
    )


def test_disabled_append_sink_does_not_create_duplicate_risk() -> None:
    manifest = _replay_manifest(
        resolved_config={
            "pipeline": {
                "sink": {
                    "silver": {"enabled": False, "mode": "append"},
                    "gold": {"enabled": False, "mode": "append"},
                }
            }
        }
    )

    assert assess_replay_write_risks(manifest) == frozenset()


@pytest.mark.parametrize("run_type", [RunType.BACKFILL, RunType.REBUILD])
def test_rebuild_family_clear_policy_creates_overwrite_risk(run_type: RunType) -> None:
    manifest = make_run_manifest(run_type=run_type)

    assert assess_replay_write_risks(manifest) == frozenset(
        {ReplayWriteRiskClassification.OVERWRITE}
    )


def test_composite_resume_replace_semantics_create_overwrite_risk() -> None:
    manifest = _replay_manifest(
        launch_context={"execution_context": "composite", "replay_mode": "resume"}
    )

    assert assess_replay_write_risks(manifest) == frozenset(
        {ReplayWriteRiskClassification.OVERWRITE}
    )
