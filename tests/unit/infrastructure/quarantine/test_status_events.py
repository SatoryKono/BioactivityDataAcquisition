# pyright: reportAny=false
# pyright: reportPrivateUsage=false
# pyright: reportUnusedCallResult=false
"""Unit tests for append-only quarantine status events."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest
from deltalake.exceptions import TableNotFoundError

from bioetl.domain.types import QuarantineRecordStatus
from bioetl.infrastructure.quarantine import status_events

pytestmark = pytest.mark.unit


def test_status_events_path_normalizes_trailing_slashes() -> None:
    assert status_events.status_events_path("/data/quarantine") == (
        "/data/quarantine_status_events"
    )
    assert status_events.status_events_path("/data/quarantine///") == (
        "/data/quarantine_status_events"
    )


def test_load_status_events_returns_empty_when_table_is_absent() -> None:
    storage_options = {"region": "local"}

    with patch.object(
        status_events,
        "DeltaTable",
        side_effect=TableNotFoundError("missing"),
    ) as delta_table:
        assert status_events._load_status_events("events", storage_options) == []

    delta_table.assert_called_once_with("events", storage_options=storage_options)


def test_load_status_events_normalizes_mapping_keys() -> None:
    delta_table = MagicMock(name="delta_table")
    storage_options = {"region": "local"}

    with (
        patch.object(status_events, "DeltaTable", return_value=delta_table),
        patch.object(
            status_events,
            "read_delta_records",
            return_value=[{1: "value", "payload_hash": "hash-a"}],
        ) as read_records,
    ):
        result = status_events._load_status_events("events", storage_options)

    assert result == [{"1": "value", "payload_hash": "hash-a"}]
    read_records.assert_called_once_with(delta_table)


def test_load_status_events_rejects_non_mapping_rows() -> None:
    with (
        patch.object(status_events, "DeltaTable", return_value=MagicMock()),
        patch.object(status_events, "read_delta_records", return_value=[["bad"]]),
        pytest.raises(
            TypeError,
            match="Quarantine status event row must be a mapping",
        ),
    ):
        status_events._load_status_events("events", None)


def test_next_status_sequence_filters_hashes_and_tolerates_invalid_sequences() -> None:
    rows = [
        {"payload_hash": "other", "status_sequence": 99},
        {"payload_hash": "hash-a", "status_sequence": "2"},
        {"payload_hash": "hash-a", "status_sequence": None},
        {"payload_hash": "hash-a", "status_sequence": "invalid"},
        {"payload_hash": "hash-a", "status_sequence": 7},
    ]

    with patch.object(status_events, "_load_status_events", return_value=rows):
        assert status_events._next_status_sequence("events", None, "hash-a") == 8
        assert status_events._next_status_sequence("events", None, "missing") == 1


def test_append_status_event_uses_append_mode_and_computed_sequence() -> None:
    storage_options = {"region": "local"}

    with (
        patch.object(status_events, "_next_status_sequence", return_value=3),
        patch.object(status_events, "write_deltalake") as write_delta,
    ):
        status_events.append_status_event(
            "events",
            storage_options,
            payload_hash="hash-a",
            new_status=QuarantineRecordStatus.IGNORED,
        )

    write_delta.assert_called_once()
    written = write_delta.call_args.kwargs
    assert written["table_or_uri"] == "events"
    assert written["mode"] == "append"
    assert written["storage_options"] is storage_options
    assert written["data"].read_all().to_pylist() == [
        {
            "payload_hash": "hash-a",
            "dq_status": "IGNORED",
            "status_sequence": 3,
        }
    ]


def test_append_status_event_falls_back_to_overwrite_for_new_table() -> None:
    with (
        patch.object(status_events, "_next_status_sequence", return_value=1),
        patch.object(
            status_events,
            "write_deltalake",
            side_effect=[TableNotFoundError("missing"), None],
        ) as write_delta,
    ):
        status_events.append_status_event(
            "events",
            None,
            payload_hash="hash-a",
            new_status=QuarantineRecordStatus.REPROCESSED,
        )

    assert write_delta.call_count == 2
    assert [item.kwargs["mode"] for item in write_delta.call_args_list] == [
        "append",
        "overwrite",
    ]
    assert write_delta.call_args_list[1].kwargs["data"].read_all().to_pylist() == [
        {
            "payload_hash": "hash-a",
            "dq_status": "REPROCESSED",
            "status_sequence": 1,
        }
    ]


def test_latest_status_filters_rows_and_uses_highest_sequence_with_latest_tie() -> None:
    rows = [
        {"payload_hash": "", "dq_status": "IGNORED", "status_sequence": 10},
        {
            "payload_hash": "not-requested",
            "dq_status": "IGNORED",
            "status_sequence": 10,
        },
        {"payload_hash": "hash-a", "dq_status": "", "status_sequence": 10},
        {
            "payload_hash": "hash-a",
            "dq_status": "NEW",
            "status_sequence": "invalid",
        },
        {
            "payload_hash": "hash-a",
            "dq_status": "IGNORED",
            "status_sequence": 2,
        },
        {
            "payload_hash": "hash-a",
            "dq_status": "REPROCESSED",
            "status_sequence": 1,
        },
        {
            "payload_hash": "hash-a",
            "dq_status": "NEW",
            "status_sequence": 2,
        },
        {
            "payload_hash": "hash-b",
            "dq_status": "IGNORED",
            "status_sequence": None,
        },
    ]

    with patch.object(status_events, "_load_status_events", return_value=rows):
        latest = status_events._latest_status_by_payload_hash(
            "events",
            None,
            {"hash-a", "hash-b"},
        )

    assert latest == {"hash-a": "NEW", "hash-b": "IGNORED"}


def test_apply_latest_statuses_returns_inputs_for_no_op_conditions() -> None:
    empty: list[dict[str, object]] = []
    assert status_events.apply_latest_statuses(empty, "events", None) is empty

    records = [{"payload_hash": "hash-a", "dq_status": "NEW"}]
    assert status_events.apply_latest_statuses(records, None, None) is records

    records_without_hash = [{"payload_hash": ""}, {"value": 1}]
    assert (
        status_events.apply_latest_statuses(records_without_hash, "events", None)
        is records_without_hash
    )

    with patch.object(
        status_events,
        "_latest_status_by_payload_hash",
        return_value={},
    ) as load_latest:
        assert status_events.apply_latest_statuses(records, "events", None) is records

    assert load_latest.call_args == call("events", None, {"hash-a"})


def test_apply_latest_statuses_overlays_matches_without_reordering_or_mutation() -> (
    None
):
    records = [
        {"payload_hash": "hash-a", "dq_status": "NEW", "ordinal": 1},
        {"payload_hash": "hash-b", "dq_status": "NEW", "ordinal": 2},
        {"ordinal": 3},
    ]

    with patch.object(
        status_events,
        "_latest_status_by_payload_hash",
        return_value={"hash-a": "REPROCESSED"},
    ):
        result = status_events.apply_latest_statuses(records, "events", None)

    assert result == [
        {"payload_hash": "hash-a", "dq_status": "REPROCESSED", "ordinal": 1},
        {"payload_hash": "hash-b", "dq_status": "NEW", "ordinal": 2},
        {"ordinal": 3},
    ]
    assert [row["ordinal"] for row in result] == [1, 2, 3]
    assert records[0]["dq_status"] == "NEW"
    assert result is not records
    assert all(
        updated is not original
        for updated, original in zip(result, records, strict=True)
    )
