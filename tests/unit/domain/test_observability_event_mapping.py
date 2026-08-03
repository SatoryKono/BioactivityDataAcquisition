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
"""Unit tests for typed Domain Event -> observability mapping."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

import pytest

from bioetl.domain.aggregates.events import (
    BatchFailed,
    BatchWritten,
    DomainEvent,
    PipelineCompleted,
    QuarantineEntryResolved,
)
from bioetl.domain.medallion import Layer
from bioetl.domain.observability_event_mapping import (
    map_domain_event_to_observability_event,
)
from bioetl.domain.types import BatchID


pytestmark = pytest.mark.unit


def test_pipeline_completed_maps_to_pipeline_finished_event() -> None:
    event = PipelineCompleted(
        occurred_at=datetime(2026, 4, 10, tzinfo=UTC),
        run_id=deterministic_run_uuid_from_callsite("test_observability_event_mapping"),
        pipeline_name="chembl_activity",
        records_processed=42,
        duration_seconds=12.5,
        stages_count=5,
    )

    envelope = map_domain_event_to_observability_event(event)

    assert envelope.event_name == "pipeline_finished"
    assert envelope.severity == "info"
    assert envelope.event_family == "pipeline.lifecycle"
    assert envelope.phase_hint == "cleanup"
    assert envelope.context["pipeline"] == "chembl_activity"
    assert envelope.context["records_processed"] == 42


def test_batch_written_maps_to_batch_family_event() -> None:
    event = BatchWritten(
        occurred_at=datetime(2026, 4, 10, tzinfo=UTC),
        run_id=deterministic_run_uuid_from_callsite("test_observability_event_mapping"),
        batch_id=BatchID("batch-1"),
        layer=Layer.SILVER,
        record_count=10,
    )

    envelope = map_domain_event_to_observability_event(event)

    assert envelope.event_name == "batch_written"
    assert envelope.event_family == "batch"
    assert envelope.phase_hint == "execution"
    assert envelope.context["layer"] == "silver"
    assert envelope.context["record_count"] == 10


def test_batch_events_reject_string_layers_inside_domain() -> None:
    event_kwargs = {
        "occurred_at": datetime(2026, 4, 10, tzinfo=UTC),
        "run_id": deterministic_run_uuid_from_callsite(
            "test_observability_event_mapping"
        ),
        "batch_id": BatchID("batch-1"),
    }

    with pytest.raises(TypeError, match=r"BatchWritten\.layer must be a Layer"):
        BatchWritten(
            **event_kwargs,
            layer="silver",  # type: ignore[arg-type]
            record_count=10,
        )

    with pytest.raises(TypeError, match=r"BatchFailed\.layer must be a Layer"):
        BatchFailed(
            **event_kwargs,
            layer="platinum",  # type: ignore[arg-type]
            error="write failed",
        )


def test_quarantine_resolution_maps_to_postrun_hint() -> None:
    event = QuarantineEntryResolved(
        occurred_at=datetime(2026, 4, 10, tzinfo=UTC),
        run_id=deterministic_run_uuid_from_callsite("test_observability_event_mapping"),
        entry_id="entry-1",
        resolution="ignored",
        resolved_by="operator",
    )

    envelope = map_domain_event_to_observability_event(event)

    assert envelope.event_name == "quarantine_entry_resolved"
    assert envelope.event_family == "quarantine"
    assert envelope.phase_hint == "postrun"
    assert envelope.context["resolution"] == "ignored"


def test_unknown_domain_event_type_raises_type_error() -> None:
    class UnknownEvent:
        occurred_at = datetime(2026, 4, 10, tzinfo=UTC)

    with pytest.raises(TypeError, match="Unsupported DomainEvent"):
        map_domain_event_to_observability_event(cast(DomainEvent, UnknownEvent()))
