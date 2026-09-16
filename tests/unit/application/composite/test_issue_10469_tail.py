"""Focused tests for one-line composite coverage residuals in issue #10469."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite._coalesce_policy_support import coalesce_and_drop
from bioetl.application.composite._lifecycle_observer_event_metrics import (
    CompositeLifecycleEventMetricsMixin,
)
from bioetl.application.composite.checkpoint._load_validation import (
    _composite_run_identity_mismatch,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.application.composite.coordinator_planning import (
    find_column_case_insensitive,
)
from bioetl.application.composite.dependency_result_mapper import _duration_seconds
from bioetl.application.composite.fsm_helper import _resolve_resume_phase
from bioetl.application.composite.helpers.column_service_layer_filter import (
    filter_columns_by_layer_config,
)
from bioetl.application.composite.helpers.cross_validator_finalize import (
    nullify_enricher_columns,
)
from bioetl.application.composite.helpers.preflight_schema_registry import (
    find_schema_class,
)
from bioetl.application.composite.join_key_normalization import (
    build_join_key_normalization_expr,
)
from bioetl.domain.composite import LayerColumnConfig
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.normalization.join_keys import JoinKeyNormalizationPolicy

pytestmark = pytest.mark.unit


def test_coalesce_and_drop_returns_result_when_no_secondary_column_remains() -> None:
    frame = MagicMock()
    result = MagicMock()
    result.columns = ["primary"]
    frame.with_columns.return_value = result
    assert coalesce_and_drop(frame, ["primary", "secondary"]) is result
    result.drop.assert_not_called()


def test_unknown_lifecycle_severity_uses_info_contract_value() -> None:
    assert CompositeLifecycleEventMetricsMixin._normalize_severity("CUSTOM") == "info"


def test_blank_expected_composite_identity_disables_identity_check() -> None:
    state = CompositeCheckpointState(composite_name="c", run_id="r")
    assert (
        _composite_run_identity_mismatch(
            state=state, expected_composite_run_identity=""
        )
        is None
    )


def test_checkpoint_with_merge_completed_updates_state_and_payload() -> None:
    stamp = datetime(2026, 1, 1, tzinfo=UTC)
    clock = SimpleNamespace(now=lambda: stamp)
    state = CompositeCheckpointState(composite_name="c", run_id="r")
    updated = state.with_merge_completed({"rows": 3}, clock=clock)
    assert updated.state is CompositePipelineState.MERGING
    assert updated.merge_completed is True
    assert updated.merge_result == {"rows": 3}
    assert updated.updated_at == stamp


def test_find_column_case_insensitive_returns_none_without_match() -> None:
    assert find_column_case_insensitive(pl.DataFrame({"Known": [1]}), "missing") is None


def test_dependency_duration_seconds_uses_wall_clock_delta() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    assert _duration_seconds(start, start + timedelta(seconds=2.5)) == 2.5


def test_resume_phase_routes_completed_merge_to_cross_validation() -> None:
    phase = _resolve_resume_phase(
        seed_completed=True,
        completed_count=2,
        total_enrichers=2,
        merge_completed=True,
    )
    assert phase.phase is CompositePipelineState.MERGING
    assert phase.description == "cross_validation (merge completed)"


def test_layer_filter_without_selection_preserves_columns() -> None:
    columns = ["a", "b"]
    assert (
        filter_columns_by_layer_config(
            columns=columns,
            layer_config=LayerColumnConfig(),
            column_groups=None,
            collect_group_columns=MagicMock(),
            logger=MagicMock(),
        )
        == columns
    )


def test_nullify_enricher_columns_returns_same_frame_without_prefixed_columns() -> None:
    frame = pl.DataFrame({"seed.id": [1]})
    assert (
        nullify_enricher_columns(
            df=frame,
            is_error=pl.Series([True]),
            enricher_provider="pubmed",
            enricher_entity="publication",
            enricher_pipeline="pubmed_publication",
            logger=MagicMock(),
        )
        is frame
    )


def test_find_schema_class_returns_none_when_module_has_no_schema_type() -> None:
    assert find_schema_class(SimpleNamespace(value=1)) is None


def test_join_key_expression_applies_lowercase_policy() -> None:
    expression = build_join_key_normalization_expr(
        column="key",
        key="custom",
        normalization_policies={
            "custom": JoinKeyNormalizationPolicy(lowercase=True),
        },
    )
    assert expression is not None
    result = pl.DataFrame({"key": ["ABC"]}).with_columns(expression)
    assert result["key"].to_list() == ["abc"]
