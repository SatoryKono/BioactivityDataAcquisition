"""Stream A leftovers: schema validators, FK helpers, anomaly monitor."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.observability.anomaly.monitor import DataQualityMonitor
from bioetl.infrastructure.schemas.composite_config_base import (
    AggregationSchema,
    EnricherSchema,
)
from bioetl.infrastructure.schemas.workflow_config import WorkflowTransformStepSchema
from bioetl.infrastructure.schemas.workflow_config_fk import (
    _normalize_fk_required_name,
    _require_fk_key_pairs_together,
    _require_matching_key_prefix,
    _validate_fk_composite_alignment,
)

pytestmark = pytest.mark.unit


def test_aggregation_order_by_duplicates() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        AggregationSchema(
            group_by="id",
            order_by=["ts", "ts"],
            fields={"n": {"source": "x", "agg": "count"}},
        )


def test_enricher_join_keys_and_aggregation_required() -> None:
    with pytest.raises(ValueError, match="empty strings"):
        EnricherSchema(
            pipeline="p",
            join_keys=[" "],
            output_fields=["f"],
        )
    with pytest.raises(ValueError, match="requires aggregation"):
        EnricherSchema(
            pipeline="p",
            join_keys=["id"],
            output_fields=["f"],
            cardinality="many_to_one",
        )


def test_fk_helpers_empty_and_mismatch() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        _normalize_fk_required_name("  ", "source_table")
    with pytest.raises(ValueError, match="together"):
        _require_fk_key_pairs_together(
            source_key="id",
            reference_key=None,
            source_keys=None,
            reference_keys=None,
        )
    with pytest.raises(ValueError, match="together"):
        _require_fk_key_pairs_together(
            source_key=None,
            reference_key=None,
            source_keys=["id"],
            reference_keys=None,
        )
    with pytest.raises(ValueError, match="must match"):
        _require_matching_key_prefix("id", ["other"], field_label="source_key")
    with pytest.raises(ValueError, match="must match"):
        _validate_fk_composite_alignment(
            source_key="id",
            reference_key="ref",
            source_keys=["id"],
            reference_keys=["other"],
        )


def test_workflow_transform_requires_config() -> None:
    with pytest.raises(ValueError, match="reconcile_rows requires config"):
        WorkflowTransformStepSchema(
            step_id="t1", transform_name="reconcile_rows", config=None
        )
    with pytest.raises(ValueError, match="reconcile_foreign_keys requires config"):
        WorkflowTransformStepSchema(
            step_id="t2", transform_name="reconcile_foreign_keys", config=None
        )


def test_monitor_skips_missing_timestamp_and_baseline() -> None:
    monitor = DataQualityMonitor(logger=MagicMock())
    monitor.detector.get_baseline_stats = MagicMock(return_value=None)  # type: ignore[method-assign]
    monitor.update_baseline_from_metrics({"latency": 1.0}, timestamp=None)
    monitor._logger.warning.assert_called()  # type: ignore[union-attr]
    assert monitor.get_baseline_stats("latency") is None
    monitor.update_baseline_from_metrics(
        {"latency": 1.0},
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
