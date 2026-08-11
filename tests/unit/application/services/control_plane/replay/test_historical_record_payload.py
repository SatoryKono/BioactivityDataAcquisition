# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportGeneralTypeIssues=false
"""Focused coverage for historical record payload helpers (#8614)."""

from __future__ import annotations

from bioetl.application.services.control_plane.replay._historical_record_payload import (
    build_historical_certification_payload,
    build_historical_certified_identity_payload,
    build_historical_run_identity_payload,
)
from bioetl.application.services.control_plane.replay.historical_identity_models import (
    HistoricalReplayRunIdentity,
)


def _identity() -> HistoricalReplayRunIdentity:
    return HistoricalReplayRunIdentity(
        manifest_id="m-1",
        run_id="r-1",
        pipeline_name="activity",
        provider="chembl",
        entity="activity",
        execution_context="batch",
    )


def test_build_historical_run_identity_payload_includes_blocking_and_extras() -> None:
    payload = build_historical_run_identity_payload(
        manifest_id="m-1",
        run_id="r-1",
        pipeline_name="activity",
        provider="chembl",
        entity="activity",
        execution_context="batch",
        certification_status="certified",
        replay_occurrence_kind="primary",
        blocking_reasons=("missing_artifact",),
        note="extra",
    )
    assert payload["manifest_id"] == "m-1"
    assert payload["blocking_reasons"] == ["missing_artifact"]
    assert payload["note"] == "extra"


def test_build_historical_certification_payload() -> None:
    payload = build_historical_certification_payload(
        certification_status="blocked",
        replay_occurrence_kind="duplicate",
        blocking_reasons=("stale",),
    )
    assert payload == {
        "certification_status": "blocked",
        "replay_occurrence_kind": "duplicate",
        "blocking_reasons": ("stale",),
    }


def test_build_historical_certified_identity_payload_from_identity() -> None:
    payload = build_historical_certified_identity_payload(
        _identity(),
        certification_status="certified",
        replay_occurrence_kind="primary",
        blocking_reasons=(),
        tag="t1",
    )
    assert payload["run_id"] == "r-1"
    assert payload["pipeline_name"] == "activity"
    assert payload["certification_status"] == "certified"
    assert payload["tag"] == "t1"
    assert payload["blocking_reasons"] == []
