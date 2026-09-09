"""Clock and duration presentation must preserve precise original evidence."""

import pytest

from bioetl.interfaces.http._identity_display_rows import identity_display_rows

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "zone,expected",
    [
        ("Europe/Kiev", "2026-09-08 08:10 EEST"),
        ("utc", "2026-09-08 05:10 UTC"),
        ("browser", "2026-09-08 05:10 UTC"),
        ("invalid", "2026-09-08 05:10 UTC"),
    ],
)
def test_identity_clock_follows_dashboard_zone(zone: str, expected: str) -> None:
    raw = "2026-09-08T05:10:43.794479+00:00"
    rows = [{"parameter": "Started at", "value": raw}]
    result = identity_display_rows(rows, zone)
    assert result[0]["value"] == expected
    assert result[0]["raw_value"] == raw
    assert rows[0]["value"] == raw


def test_duration_rounding_and_unknown_values() -> None:
    rows = [
        {"parameter": "Duration seconds", "value": "223.638948"},
        {"parameter": "Started at", "value": "UNKNOWN"},
    ]
    result = identity_display_rows(rows, "UTC")
    assert result[0] == {
        "parameter": "Duration",
        "value": "3 min 44 s",
        "raw_value": "223.638948",
    }
    assert result[1]["value"] == "UNKNOWN"


def test_identity_display_skips_non_list_and_non_dict_rows() -> None:
    assert identity_display_rows("not-a-list", "UTC") == []
    result = identity_display_rows(
        [None, "skip", {"parameter": "Run id", "value": "abc"}],
        "UTC",
    )
    assert result == [
        {"parameter": "Run id", "value": "abc", "raw_value": "abc"},
    ]


def test_naive_clock_and_invalid_duration_keep_raw_evidence() -> None:
    naive = "2026-09-08T05:10:43"
    rows = [
        {"parameter": "Started at", "value": naive},
        {"parameter": "Duration seconds", "value": "-1"},
        {"parameter": "Duration seconds", "value": "inf"},
    ]
    result = identity_display_rows(rows, "UTC")
    assert result[0]["value"] == naive
    assert result[1]["parameter"] == "Duration seconds"
    assert result[1]["value"] == "-1"
    assert result[2]["parameter"] == "Duration seconds"
    assert result[2]["value"] == "inf"


def test_timeout_display_preserves_failure_instead_of_generic_empty() -> None:
    from bioetl.interfaces.http._health_server_identity_routing_support import (
        _timeout_identity_payload,
    )

    payload = _timeout_identity_payload({"pipeline": "chembl_assay"})
    assert payload["display_rows"] == identity_display_rows(payload["rows"], "UTC")
    assert any("timed out" in row["value"] for row in payload["display_rows"])
