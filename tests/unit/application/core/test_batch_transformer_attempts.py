# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for batch transformer attempt helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from tests.helpers.deterministic_ids import deterministic_batch_uuid_from_callsite

from bioetl.application.core.base_transformer import FilteredOutError
from bioetl.application.core.batch_transformer_attempts import (
    _resolve_gold_filter_details,
    transform_record_attempt,
)
from bioetl.domain.exceptions import DataQualityError
from bioetl.domain.filtering import FilterOperator, GoldColumnFilter, GoldFilterConfig
from bioetl.domain.types import ErrorType


class _GoldFilterOwner:
    def __init__(self, filters: GoldFilterConfig) -> None:
        self._gold_filters = filters

    @property
    def gold_filters(self) -> GoldFilterConfig:
        return self._gold_filters

    def should_write_gold(self, _context, record: dict[str, object]) -> bool:
        return self._gold_filters.should_include(record)


@pytest.mark.unit
def test_resolve_gold_filter_details_returns_structured_decision() -> None:
    filters = GoldFilterConfig(
        column_filters=(
            GoldColumnFilter(
                column="bao_format",
                operator=FilterOperator.NOT_IN,
                values=frozenset({"BAO_0000218"}),
            ),
        )
    )
    owner = _GoldFilterOwner(filters)

    details = _resolve_gold_filter_details(
        owner.should_write_gold,
        {"bao_format": "BAO_0000218"},
    )

    assert details is not None
    assert details["field"] == "bao_format"
    assert details["operator"] == "not_in"
    assert details["actual"] == "BAO_0000218"
    assert details["expected"] == ["BAO_0000218"]


def _attempt_context() -> MagicMock:
    context = MagicMock()
    context.with_source_batch_id.return_value = context
    context.bind_logger.return_value = context
    context.logger = MagicMock()
    return context


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transform_record_attempt_success_path() -> None:
    """Successful transform yields silver/gold records without quarantine entries."""

    async def transform(_ctx, record, _index):
        return {"entity_id": record["id"], "value": record["value"]}

    outcome = await transform_record_attempt(
        context=_attempt_context(),
        error_classifier=MagicMock(),
        batch_metrics=MagicMock(),
        transform=transform,
        gold_filter=lambda _ctx, _rec: True,
        gold_transform=lambda _ctx, rec: {**rec, "gold": True},
        dq_config=None,
        normalization_processor=None,
        debug_export_service=None,
        raw_record={"id": "1", "value": 10},
        batch_id=deterministic_batch_uuid_from_callsite(
            "test_transform_record_attempt_success"
        ),
        index=0,
    )

    assert outcome.silver_record == {"entity_id": "1", "value": 10}
    assert outcome.gold_record == {"entity_id": "1", "value": 10, "gold": True}
    assert outcome.filtered_entry is None
    assert outcome.dq_entry is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transform_record_attempt_filtered_out_path() -> None:
    """FilteredOutError is classified into a filtered quarantine entry."""

    async def transform(_ctx, _record, _index):
        raise FilteredOutError(
            "excluded",
            details={"reason_code": "required_field_missing", "field": "x"},
        )

    batch_metrics = MagicMock()
    outcome = await transform_record_attempt(
        context=_attempt_context(),
        error_classifier=MagicMock(),
        batch_metrics=batch_metrics,
        transform=transform,
        gold_filter=lambda _ctx, _rec: True,
        gold_transform=lambda _ctx, rec: rec,
        dq_config=None,
        normalization_processor=None,
        debug_export_service=None,
        raw_record={"id": "filtered"},
        batch_id=deterministic_batch_uuid_from_callsite(
            "test_transform_record_attempt_filtered"
        ),
        index=1,
    )

    assert outcome.silver_record is None
    assert outcome.gold_record is None
    assert outcome.filtered_entry is not None
    assert outcome.dq_entry is None
    batch_metrics.track_silver_filter_rejection.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transform_record_attempt_processing_error_path() -> None:
    """TRANSFORM_PROCESSING_ERRORS produce a DQ quarantine entry."""

    async def transform(_ctx, _record, _index):
        raise DataQualityError("bad record")

    error_classifier = MagicMock()
    error_classifier.classify.return_value = ErrorType.INVALID_DATA
    batch_metrics = MagicMock()

    outcome = await transform_record_attempt(
        context=_attempt_context(),
        error_classifier=error_classifier,
        batch_metrics=batch_metrics,
        transform=transform,
        gold_filter=lambda _ctx, _rec: True,
        gold_transform=lambda _ctx, rec: rec,
        dq_config=None,
        normalization_processor=None,
        debug_export_service=None,
        raw_record={"id": "bad"},
        batch_id=deterministic_batch_uuid_from_callsite(
            "test_transform_record_attempt_dq"
        ),
        index=2,
    )

    assert outcome.silver_record is None
    assert outcome.gold_record is None
    assert outcome.filtered_entry is None
    assert outcome.dq_entry is not None
    batch_metrics.track_error.assert_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transform_attempt_projects_runtime_dq_warning_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Предупреждения runtime DQ не блокируют обработку и проецируются в Silver."""
    from bioetl.domain.behavior import dq_rule_evaluator
    from bioetl.domain.types.dq_contracts import DQDisposition

    warning = MagicMock()
    warning.disposition = DQDisposition.WARN
    warning.severity = "error"
    monkeypatch.setattr(
        dq_rule_evaluator,
        "evaluate_dq_rules_for_record",
        lambda *_args, **_kwargs: [warning],
    )
    monkeypatch.setattr(
        dq_rule_evaluator,
        "select_highest_priority_disposition",
        lambda _outcomes: DQDisposition.WARN,
    )

    async def transform(_ctx, record, _index):
        return {"entity_id": record["id"], "value": record["value"]}

    outcome = await transform_record_attempt(
        context=_attempt_context(),
        error_classifier=MagicMock(),
        batch_metrics=MagicMock(),
        transform=transform,
        gold_filter=lambda _ctx, _rec: True,
        gold_transform=lambda _ctx, rec: {**rec, "gold": True},
        dq_config=MagicMock(),
        normalization_processor=None,
        debug_export_service=None,
        raw_record={"id": "dq-warning", "value": 10},
        batch_id=deterministic_batch_uuid_from_callsite(
            "test_transform_attempt_projects_runtime_dq_warning_flags"
        ),
        index=3,
    )

    assert outcome.silver_record == {
        "entity_id": "dq-warning",
        "value": 10,
        "_dq_warn": True,
        "_dq_error": True,
    }
    assert outcome.gold_record == {
        "entity_id": "dq-warning",
        "value": 10,
        "_dq_warn": True,
        "_dq_error": True,
        "gold": True,
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transform_attempt_returns_empty_outcome_for_none_result() -> None:
    """Трансформация без записи Silver формирует пустой результат."""

    async def transform(_ctx, _record, _index):
        return None

    outcome = await transform_record_attempt(
        context=_attempt_context(),
        error_classifier=MagicMock(),
        batch_metrics=MagicMock(),
        transform=transform,
        gold_filter=lambda _ctx, _rec: True,
        gold_transform=lambda _ctx, rec: rec,
        dq_config=None,
        normalization_processor=None,
        debug_export_service=None,
        raw_record={"id": "empty"},
        batch_id=deterministic_batch_uuid_from_callsite(
            "test_transform_attempt_returns_empty_outcome_for_none_result"
        ),
        index=4,
    )

    assert outcome.silver_record is None
    assert outcome.gold_record is None
