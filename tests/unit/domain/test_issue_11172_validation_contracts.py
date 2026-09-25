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
"""Chosen contracts for the remaining domain validation findings (#11172)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from bioetl.domain._observability_contract_primitives import normalize_severity
from bioetl.domain.normalization._chembl_units import normalize_standard_unit
from bioetl.domain.normalization.profiles._standard_profile_spec import (
    coerce_standard_profile_spec,
)
from bioetl.domain.types import RunID, RunType
from bioetl.domain.value_objects.bronze_result import _normalized_path_parts
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.run_context import RunContext


pytestmark = pytest.mark.unit

_PROFILE_OVERRIDES = {
    "profile_name": "activity",
    "description": "activity profile",
    "schema_fields": ("activity_id",),
    "meta_fields": (),
}


def test_started_at_accepts_any_aware_offset_and_rejects_naive() -> None:
    """Aware offsets are accepted. Only naive datetimes are rejected (#11172)."""
    context = RunContext(
        run_id=RunID("run-1"),
        run_type=RunType.INCREMENTAL,
        started_at=datetime(2026, 9, 25, 12, 0, tzinfo=timezone(timedelta(hours=3))),
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
    )
    assert context.started_at.tzinfo is not None
    assert context.started_at.utcoffset() == timedelta(hours=3)

    with pytest.raises(ValueError, match="timezone-aware"):
        RunContext(
            run_id=RunID("run-1"),
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 9, 25, 12, 0),
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
        )
    _ = UTC


def test_negative_dq_counters_are_rejected() -> None:
    with pytest.raises(ValueError, match="DQ record counts must be non-negative"):
        BatchDQMetrics(total_records=2, error_records=-1)
    with pytest.raises(ValueError, match="error_records cannot exceed total_records"):
        BatchDQMetrics(total_records=1, error_records=2)


def test_absolute_relative_path_is_rejected_before_segment_cleanup() -> None:
    with pytest.raises(ValueError, match="relative_path must be relative"):
        _normalized_path_parts("/chembl/activity/batch.json")
    with pytest.raises(ValueError, match="relative_path must be relative"):
        _normalized_path_parts("C:/chembl/activity/batch.json")


def test_unknown_severity_aliases_fall_back_to_info() -> None:
    """warn/fatal are not vocabulary members and do not alias (#11172)."""
    assert normalize_severity("warning", fallback="debug") == "warning"
    assert normalize_severity("warn", fallback="debug") == "info"
    assert normalize_severity("fatal", fallback="debug") == "info"


def test_unknown_standard_profile_override_is_ignored() -> None:
    spec = coerce_standard_profile_spec(None, {**_PROFILE_OVERRIDES, "not_a_field": 1})
    assert spec.profile_name == "activity"
    assert not hasattr(spec, "not_a_field")


def test_metre_and_molar_aliases_share_lowercased_lookup() -> None:
    """Casefolding is intentional: ``m`` and ``M`` share one alias key (#11172)."""
    assert normalize_standard_unit("m") == normalize_standard_unit("M")
