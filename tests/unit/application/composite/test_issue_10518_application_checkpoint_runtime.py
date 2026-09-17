"""Application checkpoint-runtime coverage for #10518."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.composite.checkpoint import _checkpoint_runtime as runtime
from bioetl.application.composite.checkpoint._checkpoint_runtime import (
    _as_utc_comparable,
    _emit_checkpoint_saved_at_from_state,
    latest_checkpoint_filename,
    load_checkpoint_state,
    resolve_resume_checkpoint_filename,
)
from bioetl.domain.exceptions import BioETLError


pytestmark = pytest.mark.unit


def _payload(name: str, **overrides: object) -> str:
    base: dict[str, object] = {
        "composite_name": name,
        "run_id": "run-1",
    }
    base.update(overrides)
    return json.dumps(base)


def _storage(files: dict[str, str | None], exists: bool = False) -> MagicMock:
    storage = MagicMock()
    storage.list_glob.return_value = sorted(files)
    storage.read.side_effect = lambda path: files[path]
    storage.exists.return_value = exists
    return storage


def test_latest_returns_none_when_no_matches() -> None:
    storage = _storage({})

    assert (
        latest_checkpoint_filename(storage=storage, glob_pattern="*.json") is None
    )


def test_latest_returns_single_match_without_reading() -> None:
    storage = _storage({"only.json": None})

    assert (
        latest_checkpoint_filename(storage=storage, glob_pattern="*.json")
        == "only.json"
    )
    storage.read.assert_not_called()


def test_latest_ranks_by_newest_stamp() -> None:
    storage = _storage(
        {
            "a.json": _payload("c", updated_at="2026-09-01T10:00:00+00:00"),
            "b.json": _payload("c", updated_at="2026-09-03T10:00:00+00:00"),
            "c.json": _payload("c", created_at="2026-09-05T10:00:00+00:00"),
        }
    )

    assert (
        latest_checkpoint_filename(storage=storage, glob_pattern="*.json")
        == "c.json"
    )


def test_latest_skips_unreadable_payloads_and_falls_back_to_sorted() -> None:
    storage = MagicMock()
    storage.list_glob.return_value = ["a.json", "b.json", "c.json"]
    # None payload, invalid JSON, and missing required keys are all skipped.
    storage.read.side_effect = lambda path: {
        "a.json": None,
        "b.json": "{not-json",
        "c.json": json.dumps({"composite_name": "c"}),
    }[path]

    assert (
        latest_checkpoint_filename(storage=storage, glob_pattern="*.json")
        == "c.json"
    )


def test_latest_falls_back_to_sorted_when_states_carry_no_stamps() -> None:
    storage = _storage(
        {
            "a.json": _payload("c"),
            "b.json": _payload("c"),
        }
    )

    assert (
        latest_checkpoint_filename(storage=storage, glob_pattern="*.json")
        == "b.json"
    )


def test_latest_falls_back_to_sorted_on_mixed_naive_aware_stamps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    naive = datetime(2026, 9, 2, 10, 0, 0)
    aware = datetime(2026, 9, 3, 10, 0, 0, tzinfo=UTC)
    monkeypatch.setattr(
        runtime,
        "CompositeCheckpointState",
        SimpleNamespace(
            from_dict=lambda data: SimpleNamespace(
                updated_at=naive if data["run_id"] == "naive" else aware,
                created_at=None,
            )
        ),
    )
    monkeypatch.setattr(runtime, "_as_utc_comparable", lambda value: value)
    storage = _storage(
        {
            "a.json": json.dumps({"run_id": "naive"}),
            "b.json": json.dumps({"run_id": "aware"}),
        }
    )

    assert (
        latest_checkpoint_filename(storage=storage, glob_pattern="*.json")
        == "b.json"
    )


def test_as_utc_comparable_normalizes_naive_and_aware() -> None:
    naive = datetime(2026, 9, 1, 10, 0, 0)
    eastern = timezone(-timedelta(hours=5))

    assert _as_utc_comparable(naive) == datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    assert _as_utc_comparable(datetime(2026, 9, 1, 10, 0, tzinfo=UTC)) == datetime(
        2026, 9, 1, 10, 0, tzinfo=UTC
    )
    assert _as_utc_comparable(datetime(2026, 9, 1, 5, 0, tzinfo=eastern)) == datetime(
        2026, 9, 1, 10, 0, tzinfo=UTC
    )


def test_emit_saved_at_gauge_paths() -> None:
    _emit_checkpoint_saved_at_from_state(
        metrics=None,
        composite_name="c",
        state=SimpleNamespace(updated_at=None, created_at=None),
    )
    metrics = MagicMock()
    _emit_checkpoint_saved_at_from_state(
        metrics=metrics,
        composite_name="c",
        state=SimpleNamespace(updated_at=None, created_at=None),
    )
    metrics.set_gauge.assert_not_called()

    created = datetime(2026, 9, 4, 10, 0, tzinfo=UTC)
    _emit_checkpoint_saved_at_from_state(
        metrics=metrics,
        composite_name="c",
        state=SimpleNamespace(updated_at=None, created_at=created),
    )
    metrics.set_gauge.assert_called_once_with(
        "bioetl_checkpoint_saved_at_seconds",
        created.timestamp(),
        {"pipeline": "c"},
    )


def test_resolve_resume_prefers_explicit_filename() -> None:
    storage = _storage({"latest.json": _payload("c")}, exists=True)

    assert (
        resolve_resume_checkpoint_filename(
            storage=storage,
            checkpoint_filename="explicit.json",
            glob_pattern="*.json",
        )
        == "explicit.json"
    )
    storage.list_glob.assert_not_called()


def test_resolve_resume_falls_back_to_latest() -> None:
    storage = _storage({"latest.json": _payload("c")}, exists=False)

    assert (
        resolve_resume_checkpoint_filename(
            storage=storage,
            checkpoint_filename="missing.json",
            glob_pattern="*.json",
        )
        == "latest.json"
    )


def test_load_returns_none_when_storage_has_no_content() -> None:
    storage = _storage({"cp.json": None})
    logger = MagicMock()

    assert (
        load_checkpoint_state(
            storage=storage,
            logger=logger,
            composite_name="c",
            filename="cp.json",
        )
        is None
    )


def test_load_returns_state_with_event_metadata_and_metrics() -> None:
    payload = _payload(
        "c",
        state="seed_running",
        completed_enrichers=["enr"],
        last_event_id="evt-1",
        last_event_occurred_at="2026-09-05T10:00:00+00:00",
        updated_at="2026-09-05T11:00:00+00:00",
    )
    storage = _storage({"cp.json": payload})
    logger = MagicMock()
    metrics = MagicMock()

    state = load_checkpoint_state(
        storage=storage,
        logger=logger,
        composite_name="c",
        filename="cp.json",
        metrics=metrics,
    )

    assert state is not None
    assert state.state.value == "seed_running"
    assert state.last_event_id == "evt-1"
    metrics.set_gauge.assert_called_once()
    metrics.increment_counter.assert_called_once_with(
        "bioetl_checkpoint_load_events_total",
        1,
        {"pipeline": "c", "status": "loaded"},
    )


def test_load_without_optional_state_fields_and_metrics() -> None:
    storage = _storage({"cp.json": _payload("c")})
    logger = MagicMock()

    state = load_checkpoint_state(
        storage=storage,
        logger=logger,
        composite_name="c",
        filename="cp.json",
    )

    assert state is not None
    assert state.state.value == "not_started"


def test_load_warns_on_corrupted_state_value() -> None:
    storage = _storage({"cp.json": _payload("c", state="bogus-state")})
    logger = MagicMock()

    state = load_checkpoint_state(
        storage=storage,
        logger=logger,
        composite_name="c",
        filename="cp.json",
    )

    assert state is not None
    assert state.state.value == "not_started"
    logger.warning.assert_any_call(
        "Checkpoint state value corrupted, using default",
        composite="c",
        raw_state="bogus-state",
        parsed_state="not_started",
    )


def test_load_reports_read_failure_with_failed_counter() -> None:
    storage = MagicMock()
    storage.read.side_effect = OSError("disk gone")
    logger = MagicMock()
    metrics = MagicMock()

    assert (
        load_checkpoint_state(
            storage=storage,
            logger=logger,
            composite_name="c",
            filename="cp.json",
            metrics=metrics,
        )
        is None
    )
    logger.warning.assert_called_once()
    assert logger.warning.call_args.args[0] == "Failed to load checkpoint"
    assert logger.warning.call_args.kwargs["reason_code"] == "checkpoint_load_failed"
    metrics.increment_counter.assert_called_once_with(
        "bioetl_checkpoint_load_events_total",
        1,
        {"pipeline": "c", "status": "failed"},
    )


def test_load_reports_invalid_json_without_metrics() -> None:
    storage = MagicMock()
    storage.read.return_value = "{not-json"
    logger = MagicMock()

    assert (
        load_checkpoint_state(
            storage=storage,
            logger=logger,
            composite_name="c",
            filename="cp.json",
        )
        is None
    )
    logger.warning.assert_called_once()


def test_load_reports_unexpected_bioetl_error() -> None:
    storage = MagicMock()
    storage.read.side_effect = BioETLError("backend exploded")
    logger = MagicMock()

    assert (
        load_checkpoint_state(
            storage=storage,
            logger=logger,
            composite_name="c",
            filename="cp.json",
        )
        is None
    )
    logger.warning.assert_called_once()
    assert (
        logger.warning.call_args.kwargs["reason_code"] == "unexpected_bioetl_error"
    )


def test_load_reports_unexpected_bioetl_error_with_failed_counter() -> None:
    storage = MagicMock()
    storage.read.side_effect = BioETLError("backend exploded")
    logger = MagicMock()
    metrics = MagicMock()

    assert (
        load_checkpoint_state(
            storage=storage,
            logger=logger,
            composite_name="c",
            filename="cp.json",
            metrics=metrics,
        )
        is None
    )
    metrics.increment_counter.assert_called_once_with(
        "bioetl_checkpoint_load_events_total",
        1,
        {"pipeline": "c", "status": "failed"},
    )
