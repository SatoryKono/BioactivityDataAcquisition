"""Behavioral tests for composite checkpoint loading helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from bioetl.application.composite.checkpoint._checkpoint_runtime import (
    _as_utc_comparable,
    _emit_checkpoint_saved_at_from_state,
    latest_checkpoint_filename,
    load_checkpoint_state,
    resolve_resume_checkpoint_filename,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.exceptions import BioETLError

pytestmark = pytest.mark.unit


def _serialized_state(
    *, updated_at: datetime | None = None, created_at: datetime | None = None
) -> str:
    state = CompositeCheckpointState(
        composite_name="chembl_composite",
        run_id="run-1",
        updated_at=updated_at,
        created_at=created_at,
        last_event_occurred_at=updated_at,
    )
    return json.dumps(state.to_dict())


@pytest.mark.parametrize(
    ("matches", "expected"),
    [([], None), (["only.json"], "only.json")],
)
def test_latest_checkpoint_filename_handles_zero_or_one_match(
    matches: list[str], expected: str | None
) -> None:
    storage = MagicMock()
    storage.list_glob.return_value = matches
    assert latest_checkpoint_filename(storage=storage, glob_pattern="*.json") == expected
    storage.read.assert_not_called()


def test_latest_checkpoint_filename_ranks_valid_timestamps_and_skips_bad_entries() -> None:
    old = datetime(2026, 1, 1)
    new = datetime(2026, 1, 2, tzinfo=UTC)
    storage = MagicMock()
    storage.list_glob.return_value = ["missing", "broken", "old", "new"]
    storage.read.side_effect = [
        None,
        "not-json",
        _serialized_state(created_at=old),
        _serialized_state(updated_at=new),
    ]

    assert (
        latest_checkpoint_filename(storage=storage, glob_pattern="*.json") == "new"
    )


def test_latest_checkpoint_filename_falls_back_to_sorted_name_without_timestamps() -> None:
    storage = MagicMock()
    storage.list_glob.return_value = ["b.json", "a.json"]
    storage.read.return_value = _serialized_state()
    assert latest_checkpoint_filename(storage=storage, glob_pattern="*.json") == "b.json"


def test_latest_checkpoint_filename_has_deterministic_fallback_for_unorderable_rank() -> None:
    storage = MagicMock()
    storage.list_glob.return_value = ["b.json", "a.json"]
    storage.read.side_effect = [
        _serialized_state(created_at=datetime(2026, 1, 1, tzinfo=UTC)),
        _serialized_state(created_at=datetime(2026, 1, 2, tzinfo=UTC)),
    ]
    with patch(
        "bioetl.application.composite.checkpoint._checkpoint_runtime.max",
        side_effect=TypeError("unorderable"),
        create=True,
    ):
        assert latest_checkpoint_filename(storage=storage, glob_pattern="*.json") == "b.json"


def test_as_utc_comparable_normalizes_naive_and_aware_values() -> None:
    naive = datetime(2026, 1, 1, 12, 0)
    offset = datetime(2026, 1, 1, 14, 0, tzinfo=UTC) + timedelta(0)
    assert _as_utc_comparable(naive).tzinfo is UTC
    assert _as_utc_comparable(offset) == offset.astimezone(UTC)


def test_emit_checkpoint_saved_at_requires_metrics_and_timestamp() -> None:
    empty = CompositeCheckpointState(composite_name="c", run_id="r")
    metrics = MagicMock()
    _emit_checkpoint_saved_at_from_state(metrics=None, composite_name="c", state=empty)
    _emit_checkpoint_saved_at_from_state(metrics=metrics, composite_name="c", state=empty)
    metrics.set_gauge.assert_not_called()


def test_emit_checkpoint_saved_at_uses_updated_timestamp() -> None:
    stamp = datetime(2026, 1, 1, tzinfo=UTC)
    state = CompositeCheckpointState(
        composite_name="c", run_id="r", created_at=stamp, updated_at=stamp
    )
    metrics = MagicMock()
    _emit_checkpoint_saved_at_from_state(metrics=metrics, composite_name="c", state=state)
    metrics.set_gauge.assert_called_once_with(
        "bioetl_checkpoint_saved_at_seconds", stamp.timestamp(), {"pipeline": "c"}
    )


def test_resolve_resume_checkpoint_prefers_explicit_existing_file() -> None:
    storage = MagicMock()
    storage.exists.return_value = True
    assert (
        resolve_resume_checkpoint_filename(
            storage=storage,
            checkpoint_filename="explicit.json",
            glob_pattern="*.json",
        )
        == "explicit.json"
    )
    storage.list_glob.assert_not_called()


def test_resolve_resume_checkpoint_uses_latest_fallback() -> None:
    storage = MagicMock()
    storage.exists.return_value = False
    storage.list_glob.return_value = ["latest.json"]
    assert (
        resolve_resume_checkpoint_filename(
            storage=storage,
            checkpoint_filename="missing.json",
            glob_pattern="*.json",
        )
        == "latest.json"
    )


def test_load_checkpoint_state_returns_none_for_missing_content() -> None:
    storage = MagicMock()
    storage.read.return_value = None
    logger = MagicMock()
    assert (
        load_checkpoint_state(
            storage=storage, logger=logger, composite_name="c", filename="missing"
        )
        is None
    )
    logger.info.assert_not_called()


def test_load_checkpoint_state_logs_corruption_and_emits_metrics() -> None:
    stamp = datetime(2026, 1, 1, tzinfo=UTC)
    payload = json.loads(_serialized_state(updated_at=stamp))
    payload["state"] = "invalid-state"
    storage = MagicMock()
    storage.read.return_value = json.dumps(payload)
    logger = MagicMock()
    metrics = MagicMock()

    state = load_checkpoint_state(
        storage=storage,
        logger=logger,
        composite_name="chembl_composite",
        filename="checkpoint.json",
        metrics=metrics,
    )

    assert state is not None
    logger.warning.assert_called_once()
    logger.info.assert_called_once()
    metrics.set_gauge.assert_called_once()
    metrics.increment_counter.assert_called_once_with(
        "bioetl_checkpoint_load_events_total",
        1,
        {"pipeline": "chembl_composite", "status": "loaded"},
    )


@pytest.mark.parametrize(
    ("error", "reason_code"),
    [
        (ValueError("invalid"), "checkpoint_load_failed"),
        (BioETLError("domain failure"), "unexpected_bioetl_error"),
    ],
)
def test_load_checkpoint_state_maps_expected_failures_to_none(
    error: Exception, reason_code: str
) -> None:
    storage = MagicMock()
    storage.read.side_effect = error
    logger = MagicMock()
    metrics = MagicMock()

    assert (
        load_checkpoint_state(
            storage=storage,
            logger=logger,
            composite_name="c",
            filename="checkpoint.json",
            metrics=metrics,
        )
        is None
    )
    assert logger.warning.call_args.kwargs["reason_code"] == reason_code
    metrics.increment_counter.assert_called_once_with(
        "bioetl_checkpoint_load_events_total",
        1,
        {"pipeline": "c", "status": "failed"},
    )
