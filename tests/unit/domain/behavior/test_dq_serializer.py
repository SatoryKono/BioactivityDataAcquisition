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
"""Unit tests for DQ report serializer behavior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

import pytest

from bioetl.domain.behavior.dq_serializer import DQReportSerializer, to_dict
from bioetl.domain.medallion import Layer
from bioetl.domain.value_objects.dq_report import (
    BronzeDQReport,
    DQCheckStatus,
    DQReportFormat,
    DQReportStatus,
    DQReportSummary,
)

pytestmark = pytest.mark.unit


class _Enum(Enum):
    VALUE = "value"


@dataclass(frozen=True)
class _Nested:
    when: datetime
    state: _Enum
    payload: tuple[object, ...]


def _report() -> BronzeDQReport:
    return BronzeDQReport(
        layer=Layer.BRONZE,
        timestamp=datetime(2026, 6, 16, tzinfo=UTC),
        run_id="run-1",
        pipeline="chembl_activity",
        batch_id="batch-1",
        source_file="bronze.jsonl",
        checks={
            "record_count": {
                "status": DQCheckStatus.PASS,
                "details": {"count": 10},
            }
        },
        summary=DQReportSummary(
            total_checks=1,
            passed=1,
            failed=0,
            warnings=0,
            overall_status=DQReportStatus.PASS,
        ),
    )


def test_to_dict_serializes_dataclass_enum_datetime_and_collections() -> None:
    payload = to_dict(
        {
            "nested": _Nested(
                when=datetime(2026, 6, 16, tzinfo=UTC),
                state=_Enum.VALUE,
                payload=(_Enum.VALUE, {"x": datetime(2026, 6, 16, tzinfo=UTC)}),
            )
        }
    )

    assert payload["nested"]["state"] == "value"
    assert payload["nested"]["payload"][0] == "value"
    assert payload["nested"]["when"] == "2026-06-16T00:00:00+00:00"
    assert to_dict("plain") == {"value": "plain"}


def test_serializer_outputs_json_yaml_and_html() -> None:
    serializer = DQReportSerializer()
    report = _report()

    json_payload = serializer.serialize(report, DQReportFormat.JSON)
    yaml_payload = serializer.serialize(report, DQReportFormat.YAML)
    html_payload = serializer.serialize(report, DQReportFormat.HTML)

    assert '"pipeline": "chembl_activity"' in json_payload
    assert "pipeline: chembl_activity" in yaml_payload
    assert "<html" in html_payload.lower()
    assert serializer.to_dict(report)["layer"] == "bronze"


def test_yaml_helpers_quote_special_strings_and_render_lists() -> None:
    serializer = DQReportSerializer()

    yaml_payload = serializer._dict_to_yaml(
        {
            "plain": "value",
            "with_colon": "a: b",
            "with_hash": "a # b",
            "none": None,
            "truth": True,
            "items": [{"name": "x"}, "y"],
        }
    )

    assert "plain: value" in yaml_payload
    assert 'with_colon: "a: b"' in yaml_payload
    assert 'with_hash: "a # b"' in yaml_payload
    assert "none: null" in yaml_payload
    assert "truth: true" in yaml_payload
    assert "  -" in yaml_payload


def test_html_helper_delegates_rendering_components() -> None:
    serializer = DQReportSerializer()

    assert serializer._status_color("passed") == "pass"
    assert "No checks" in serializer._render_checks_html({})
    assert "<table" in serializer._render_check_details({"count": 1})
    assert "count" in serializer._format_detail_value({"count": 1})
    thresholds_html = serializer._render_thresholds_html({"soft_fail_threshold": 0.1})
    assert "DQ Thresholds" in thresholds_html
    assert "pass" in thresholds_html


def test_unsupported_format_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unsupported format"):
        DQReportSerializer().serialize(_report(), object())  # type: ignore[arg-type]
