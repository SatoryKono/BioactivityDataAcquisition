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
"""Focused tests for control-plane selector filtering helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from bioetl.interfaces.http import _control_plane_selector_filters as subject
from bioetl.interfaces.http._control_plane_selector_records import SelectorRecord

pytestmark = pytest.mark.unit


def _record(
    suffix: str,
    *,
    workflow_candidates: tuple[str, ...],
    pipeline: str,
    run_type: str,
    run_status: str,
    completed_offset: int,
) -> SelectorRecord:
    stamp = datetime(2026, 7, 7, 9, 0, tzinfo=UTC) + timedelta(minutes=completed_offset)
    return SelectorRecord(
        manifest=cast(Any, None),
        workflow=workflow_candidates[0],
        workflow_candidates=workflow_candidates,
        pipeline=pipeline,
        run_type=run_type,
        run_id=f"run-{suffix}",
        provider=pipeline.split("_", 1)[0],
        entity=pipeline.split("_", 1)[-1],
        manifest_id=f"manifest-{suffix}",
        started_at=stamp,
        started_at_source="test",
        completed_at=stamp,
        completed_at_source="test",
        run_status=run_status,
        terminal_event_type=None,
    )


def test_filter_records_honors_exact_run_id_before_other_dimensions() -> None:
    first = _record(
        "1",
        workflow_candidates=("wf-a",),
        pipeline="chembl_activity",
        run_type="incremental",
        run_status="success",
        completed_offset=1,
    )
    second = _record(
        "2",
        workflow_candidates=("wf-b",),
        pipeline="pubchem_compound",
        run_type="backfill",
        run_status="failed",
        completed_offset=2,
    )

    assert subject.filter_records(
        (first, second),
        selected_workflows=("wf-a",),
        selected_pipelines=("chembl_activity",),
        selected_run_types=("incremental",),
        selected_run_statuses=("success",),
        selected_run_id="run-2",
    ) == (second,)


def test_filter_records_ignores_lowercase_all_scope_tokens() -> None:
    """Literal 'all' must not filter as a run_type/workflow label."""
    first = _record(
        "1",
        workflow_candidates=("wf-a",),
        pipeline="chembl_assay",
        run_type="backfill",
        run_status="success",
        completed_offset=1,
    )
    second = _record(
        "2",
        workflow_candidates=("wf-b",),
        pipeline="chembl_assay",
        run_type="incremental",
        run_status="success",
        completed_offset=2,
    )
    assert subject.filter_records(
        (first, second),
        selected_workflows=("all",),
        selected_pipelines=("chembl_assay",),
        selected_run_types=("all",),
        selected_run_statuses=(),
        selected_run_id=None,
    ) == (first, second)


def test_filter_records_requires_all_selected_dimensions_to_match() -> None:
    first = _record(
        "1",
        workflow_candidates=("wf-a", "wf-shared"),
        pipeline="chembl_activity",
        run_type="incremental",
        run_status="success",
        completed_offset=1,
    )
    second = _record(
        "2",
        workflow_candidates=("wf-b", "wf-shared"),
        pipeline="chembl_target",
        run_type="incremental",
        run_status="success",
        completed_offset=2,
    )
    third = _record(
        "3",
        workflow_candidates=("wf-c",),
        pipeline="chembl_activity",
        run_type="backfill",
        run_status="success",
        completed_offset=3,
    )

    assert subject.filter_records(
        (first, second, third),
        selected_workflows=("wf-shared",),
        selected_pipelines=("chembl_activity",),
        selected_run_types=("incremental",),
        selected_run_statuses=("success",),
        selected_run_id=None,
    ) == (first,)


def test_run_id_options_order_by_started_at_desc_independent_of_input_order() -> None:
    """#7552: filter-options run_id list is newest-start-first, not catalog order."""
    from bioetl.interfaces.http._control_plane_selector_payloads import (
        RUN_ID_NO_SELECTION,
        defaults_payload,
        options_payload,
    )

    older = _record(
        "older",
        workflow_candidates=("wf-a",),
        pipeline="chembl_activity",
        run_type="backfill",
        run_status="success",
        completed_offset=1,
    )
    newer = _record(
        "newer",
        workflow_candidates=("wf-a",),
        pipeline="chembl_activity",
        run_type="backfill",
        run_status="success",
        completed_offset=10,
    )
    middle = _record(
        "middle",
        workflow_candidates=("wf-a",),
        pipeline="chembl_activity",
        run_type="incremental",
        run_status="success",
        completed_offset=5,
    )

    # Deliberately reverse catalog encounter order.
    options = options_payload((older, newer, middle))
    assert options["run_id"] == ["run-newer", "run-middle", "run-older"]

    defaults = defaults_payload()
    assert defaults["policy"] == "last_run_truthful"
    assert defaults["run_type_fallback"] == "backfill"
    assert defaults["run_id_list_order"] == "started_at_desc"
    assert RUN_ID_NO_SELECTION == "-"


def test_latest_record_uses_completed_at_then_manifest_id_tie_breaker() -> None:
    older = _record(
        "a",
        workflow_candidates=("wf-a",),
        pipeline="chembl_activity",
        run_type="incremental",
        run_status="success",
        completed_offset=1,
    )
    same_time_lower_manifest = _record(
        "b",
        workflow_candidates=("wf-a",),
        pipeline="chembl_activity",
        run_type="incremental",
        run_status="success",
        completed_offset=2,
    )
    same_time_higher_manifest = _record(
        "c",
        workflow_candidates=("wf-a",),
        pipeline="chembl_activity",
        run_type="incremental",
        run_status="success",
        completed_offset=2,
    )

    assert subject.latest_record(()) is None
    assert (
        subject.latest_record(
            (older, same_time_lower_manifest, same_time_higher_manifest)
        )
        is same_time_higher_manifest
    )
