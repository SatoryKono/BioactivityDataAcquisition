"""Stream B APP: leftover preview, metrics increment, posix-map, and closure verdict."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.core.base_transformer._structural_policy_events import preview_value
from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.application.services.control_plane.replay.historical_closure_policy import (
    resolve_closure_verdict,
)
from bioetl.application.services.run_reports.source_identity import (
    runtime_path_to_local_path,
)

pytestmark = pytest.mark.unit


def test_preview_value_truncates_long_repr() -> None:
    preview = preview_value("x" * 200, field_name="molecule_id", max_length=20)
    assert preview.endswith("...")
    assert len(preview) == 20


def test_pipeline_metrics_increments_when_count_positive() -> None:
    metrics = MagicMock()
    recorder = PipelineMetricsRecorder(pipeline="chembl_activity", metrics=metrics)
    recorder.record_output_artifact_publication(stage="gold", status="ok", count=2)
    metrics.increment_counter.assert_called_once()


def test_runtime_path_returns_mapped_posix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bioetl.application.services.run_reports.source_identity.os.name",
        "posix",
    )
    monkeypatch.setattr(
        "bioetl.application.services.run_reports.source_identity._mapped_runtime_path",
        lambda value: "/mnt/c/data" if "C:" in value or "c:" in value.lower() else None,
    )
    assert runtime_path_to_local_path("C:/data", root="/tmp") == Path("/mnt/c/data")


def test_closure_verdict_unsupported_scope() -> None:
    inventory = SimpleNamespace(
        manifest_count=2,
        certified_count=0,
        replayable_count=0,
        unsupported_count=3,
        remaining_uncertified_count=2,
    )
    verdict, reason = resolve_closure_verdict(
        inventory=inventory,  # type: ignore[arg-type]
        unresolved_records=(),
        disposition_map={},
        claim_scope_mode="all_retained_historical_runs",
    )
    assert verdict == "outside_supported_scope_present"
    assert "outside_the_current_supported" in reason
