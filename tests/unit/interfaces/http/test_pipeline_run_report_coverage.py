# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Owner tests for pipeline run-report coverage helpers (#9400)."""

from __future__ import annotations

import pytest

from bioetl.interfaces.http._pipeline_run_report_coverage import (
    _coverage_chip,
    _coverage_fields,
    _coverage_offset_outside,
    _padded_range_ms,
    _parse_grafana_ms,
    _parse_iso_to_ms,
)

pytestmark = pytest.mark.unit


def test_parse_iso_to_ms_rejects_blank_and_invalid_tokens() -> None:
    assert _parse_iso_to_ms(None) is None
    assert _parse_iso_to_ms("") is None
    assert _parse_iso_to_ms("   ") is None
    assert _parse_iso_to_ms("not-iso") is None


def test_parse_iso_to_ms_accepts_zulu_and_naive_local_as_utc() -> None:
    zulu = _parse_iso_to_ms("2026-08-10T00:00:00Z")
    naive = _parse_iso_to_ms("2026-08-10T00:00:00")
    assert zulu is not None and naive is not None
    assert zulu == naive


def test_parse_grafana_ms_parses_epoch_or_rejects() -> None:
    assert _parse_grafana_ms(None) is None
    assert _parse_grafana_ms("  ") is None
    assert _parse_grafana_ms("abc") is None
    assert _parse_grafana_ms("1000") == 1000
    assert _parse_grafana_ms(2000) == 2000


def test_coverage_chip_maps_projection_to_first_window_label() -> None:
    assert _coverage_chip("yes") == "IN RANGE"
    assert _coverage_chip("outside") == "OUT OF RANGE"
    assert _coverage_chip("partial") == "OUT OF RANGE"
    assert _coverage_chip("unknown") == "UNKNOWN"


def test_coverage_fields_status_and_missing_range_branches() -> None:
    assert _coverage_fields(
        started_ms=1,
        completed_ms=2,
        grafana_from_ms=0,
        grafana_to_ms=10,
        status="unresolved_scope",
    ) == ("select_run", "")
    assert _coverage_fields(
        started_ms=1,
        completed_ms=2,
        grafana_from_ms=0,
        grafana_to_ms=10,
        status="not_found",
    ) == ("not_found", "")
    assert _coverage_fields(
        started_ms=None,
        completed_ms=None,
        grafana_from_ms=1,
        grafana_to_ms=2,
        status="ok",
    ) == ("unknown", "")
    assert _coverage_fields(
        started_ms=10,
        completed_ms=20,
        grafana_from_ms=None,
        grafana_to_ms=None,
        status="ok",
    ) == ("range_unspecified", "")


def test_coverage_fields_inside_outside_and_partial_windows() -> None:
    assert _coverage_fields(
        started_ms=10,
        completed_ms=20,
        grafana_from_ms=0,
        grafana_to_ms=30,
        status="ok",
    ) == ("yes", "0h")
    covers, offset = _coverage_fields(
        started_ms=10,
        completed_ms=20,
        grafana_from_ms=50,
        grafana_to_ms=80,
        status="ok",
    )
    assert covers == "outside"
    assert "before window" in offset
    covers, offset = _coverage_fields(
        started_ms=90,
        completed_ms=100,
        grafana_from_ms=50,
        grafana_to_ms=80,
        status="ok",
    )
    assert covers == "outside"
    assert "after window" in offset
    covers, offset = _coverage_fields(
        started_ms=10,
        completed_ms=90,
        grafana_from_ms=50,
        grafana_to_ms=80,
        status="ok",
    )
    assert covers == "partial"
    assert offset == "overlaps window"


def test_coverage_offset_outside_and_padded_range_ms() -> None:
    covers, offset = _coverage_offset_outside(
        started_ms=10,
        end_ms=20,
        grafana_from_ms=50,
        grafana_to_ms=80,
    )
    assert covers == "outside"
    assert "before window" in offset
    from_ms, to_ms = _padded_range_ms(None, None)
    assert from_ms == ""
    assert to_ms == ""
    pad_ms = 5 * 60 * 1000
    started_ms = 1_000_000
    from_ms, to_ms = _padded_range_ms(started_ms, None)
    assert from_ms == str(started_ms - pad_ms)
    assert to_ms == str(started_ms + pad_ms)
    from_ms, to_ms = _padded_range_ms(started_ms, started_ms + 20_000)
    assert from_ms == str(started_ms - pad_ms)
    assert to_ms == str(started_ms + 20_000 + pad_ms)
