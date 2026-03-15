"""Unit tests for batch_transformer_helpers compatibility re-exports."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_batch_transformer_helpers_reexport_canonical_symbols() -> None:
    """Legacy helper facade should re-export canonical batch-transform helpers."""
    from bioetl.application.core import batch_transformer_attempts
    from bioetl.application.core import batch_transformer_helpers
    from bioetl.application.core import batch_transformer_orchestration
    from bioetl.application.core import batch_transformer_quarantine
    from bioetl.application.core import batch_transformer_state

    assert (
        batch_transformer_helpers.RecordTransformOutcome
        is batch_transformer_state.RecordTransformOutcome
    )
    assert (
        batch_transformer_helpers.TransformResult
        is batch_transformer_state.TransformResult
    )
    assert (
        batch_transformer_helpers.TransformedRecord
        is batch_transformer_state.TransformedRecord
    )
    assert (
        batch_transformer_helpers.apply_stream_transform_result_to_state
        is batch_transformer_state.apply_stream_transform_result_to_state
    )
    assert (
        batch_transformer_helpers.apply_transform_outcome_to_state
        is batch_transformer_state.apply_transform_outcome_to_state
    )
    assert (
        batch_transformer_helpers.build_transform_result
        is batch_transformer_state.build_transform_result
    )
    assert (
        batch_transformer_helpers.create_transform_aggregation_state
        is batch_transformer_state.create_transform_aggregation_state
    )
    assert (
        batch_transformer_helpers.transform_record_attempt
        is batch_transformer_attempts.transform_record_attempt
    )
    assert (
        batch_transformer_helpers.flush_dq_records
        is batch_transformer_quarantine.flush_dq_records
    )
    assert (
        batch_transformer_helpers.flush_filtered_records
        is batch_transformer_quarantine.flush_filtered_records
    )
    assert (
        batch_transformer_helpers.route_single_transform_attempt
        is batch_transformer_quarantine.route_single_transform_attempt
    )
    assert (
        batch_transformer_helpers.yield_control_if_needed
        is batch_transformer_orchestration.yield_control_if_needed
    )
