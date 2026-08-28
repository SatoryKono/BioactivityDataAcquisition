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
from bioetl.application.core.batch_transformer_attempt_success import (
    _apply_runtime_dq_outcomes,
    _finalize_transformed_record,
    _resolve_gold_filter_details as _resolve_success_gold_filter_details,
    build_transform_success_outcome,
    resolve_transform_result,
)
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.domain.behavior import dq_rule_evaluator
from bioetl.domain.exceptions import DataQualityError
from bioetl.domain.filtering import FilterOperator, GoldColumnFilter, GoldFilterConfig
from bioetl.domain.types import ErrorType
from bioetl.domain.types.dq_contracts import DQDisposition, DQRuleOutcome


class _GoldFilterOwner:
    def __init__(self, filters: GoldFilterConfig) -> None:
        self._gold_filters = filters

    @property
    def gold_filters(self) -> GoldFilterConfig:
        return self._gold_filters

    def should_write_gold(self, _context, record: dict[str, object]) -> bool:
        return self._gold_filters.should_include(record)


class _LegacyGoldFilterWithoutEvaluator:
    _gold_filters = object()

    def should_write_gold(self, _context, _record: dict[str, object]) -> bool:
        return False


class _UnstructuredGoldFilterEvaluator:
    class _Filters:
        @staticmethod
        def evaluate(_record: dict[str, object]) -> object:
            return object()

    gold_filters = _Filters()

    def should_write_gold(self, _context, _record: dict[str, object]) -> bool:
        return False


class _LegacyGoldFilterOwner:
    def __init__(self, filters: object) -> None:
        self._gold_filters = filters

    def should_write_gold(self, _context, _record: dict[str, object]) -> bool:
        return False


@pytest.mark.unit
def test_gold_filter_details_without_bound_owner_are_unavailable() -> None:
    assert _resolve_gold_filter_details(lambda _ctx, _record: False, {}) is None


@pytest.mark.unit
def test_gold_filter_details_without_callable_evaluator_are_unavailable() -> None:
    owner = _LegacyGoldFilterOwner(object())

    assert _resolve_gold_filter_details(owner.should_write_gold, {}) is None


@pytest.mark.unit
def test_finalize_transformed_record_handles_all_normalization_modes() -> None:
    context = _attempt_context()
    processor = MagicMock()
    processor.finalize_pre_silver.return_value = {"stage": "silver"}
    processor.normalize_record.return_value = {"stage": "normalized"}
    staged = PreSilverRecord(
        entity_id="1",
        business_data={"value": 1},
        build_silver_record=MagicMock(),
    )

    assert (
        _finalize_transformed_record(
            transformed=None,
            normalization_processor=processor,
            context=context,
            index=0,
        )
        is None
    )
    assert _finalize_transformed_record(
        transformed=staged,
        normalization_processor=processor,
        context=context,
        index=1,
    ) == {"stage": "silver"}
    assert _finalize_transformed_record(
        transformed={"value": 1},
        normalization_processor=processor,
        context=context,
        index=2,
    ) == {"stage": "normalized"}


@pytest.mark.unit
def test_pre_silver_record_requires_normalization_processor() -> None:
    staged = PreSilverRecord(
        entity_id="1",
        business_data={"value": 1},
        build_silver_record=MagicMock(),
    )

    with pytest.raises(
        RuntimeError,
        match="PreSilverRecord requires RecordNormalizationProcessor",
    ):
        _finalize_transformed_record(
            transformed=staged,
            normalization_processor=None,
            context=_attempt_context(),
            index=0,
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_transform_result_awaits_async_value() -> None:
    async def transformed() -> dict[str, object]:
        return {"value": 1}

    assert await resolve_transform_result(transformed()) == {"value": 1}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_transform_success_outcome_records_contract_exclusion() -> None:
    debug_export = MagicMock()

    outcome = await build_transform_success_outcome(
        context=_attempt_context(),
        transform=lambda _ctx, record, _index: {"entity_id": record["id"]},
        raw_record={"id": "1"},
        index=3,
        normalization_processor=None,
        gold_filter=lambda _ctx, _record: False,
        gold_transform=lambda _ctx, record: record,
        dq_config=None,
        debug_export_service=debug_export,
    )

    assert outcome.silver_record == {"entity_id": "1"}
    assert outcome.gold_record is None
    assert outcome.gold_excluded_by_contract is True
    debug_export.record_transform_success.assert_called_once_with(
        raw_record={"id": "1"},
        record_index=3,
        silver_record={"entity_id": "1"},
        gold_record=None,
        gold_excluded_by_contract=True,
        gold_filter_details=None,
    )


@pytest.mark.unit
def test_runtime_dq_outcomes_project_warning_flags(monkeypatch) -> None:
    outcome = DQRuleOutcome(
        rule_id="warn-rule",
        violation_kind="business_rule_violation",
        severity="error",
        disposition=DQDisposition.WARN,
    )
    monkeypatch.setattr(
        "bioetl.domain.behavior.dq_rule_evaluator.evaluate_dq_rules_for_record",
        lambda _record, _config: [outcome],
    )

    assert _apply_runtime_dq_outcomes(
        silver_record={"entity_id": "1"},
        dq_config=MagicMock(),
    ) == {"entity_id": "1", "_dq_warn": True, "_dq_error": True}


@pytest.mark.unit
def test_runtime_dq_outcomes_raise_for_blocking_disposition(monkeypatch) -> None:
    outcome = DQRuleOutcome(
        rule_id="fail-rule",
        violation_kind="business_rule_violation",
        severity="error",
        disposition=DQDisposition.FAIL,
    )
    monkeypatch.setattr(
        "bioetl.domain.behavior.dq_rule_evaluator.evaluate_dq_rules_for_record",
        lambda _record, _config: [outcome],
    )

    with pytest.raises(
        DataQualityError,
        match=r"disposition=fail; rules=\[fail-rule\]",
    ):
        _apply_runtime_dq_outcomes(
            silver_record={"entity_id": "1"},
            dq_config=MagicMock(),
        )


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


@pytest.mark.unit
def test_resolve_gold_filter_details_handles_legacy_non_evaluator() -> None:
    owner = _LegacyGoldFilterWithoutEvaluator()

    details = _resolve_success_gold_filter_details(
        owner.should_write_gold,
        {"bao_format": "BAO_0000218"},
    )

    assert details is None


@pytest.mark.unit
def test_resolve_gold_filter_details_ignores_unstructured_evaluator_result() -> None:
    owner = _UnstructuredGoldFilterEvaluator()

    details = _resolve_success_gold_filter_details(
        owner.should_write_gold,
        {"bao_format": "BAO_0000218"},
    )

    assert details is None


@pytest.mark.unit
def test_apply_runtime_dq_outcomes_projects_warn_and_error_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome = MagicMock(
        disposition=DQDisposition.WARN,
        severity="error",
        rule_id="runtime.warn",
    )
    monkeypatch.setattr(
        dq_rule_evaluator,
        "evaluate_dq_rules_for_record",
        lambda _record, _config: [outcome],
    )
    monkeypatch.setattr(
        dq_rule_evaluator,
        "select_highest_priority_disposition",
        lambda _outcomes: DQDisposition.WARN,
    )

    projected = _apply_runtime_dq_outcomes(
        silver_record={"entity_id": "1"},
        dq_config=MagicMock(),
    )

    assert projected == {
        "entity_id": "1",
        "_dq_warn": True,
        "_dq_error": True,
    }


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
