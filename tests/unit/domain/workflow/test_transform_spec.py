"""Tests for workflow transform identity fingerprints."""

from __future__ import annotations

import pytest

from bioetl.domain.workflow import TransformStepConfig, WorkflowTransformSpec


pytestmark = pytest.mark.unit


def test_transform_fingerprint_is_stable_for_config_key_order() -> None:
    left = WorkflowTransformSpec.from_step(
        TransformStepConfig(
            step_id="normalize",
            transform_name="normalize_activity",
            depends_on=("extract",),
            config={"b": 2, "a": {"z": 1, "y": 2}},
        )
    )
    right = WorkflowTransformSpec.from_step(
        TransformStepConfig(
            step_id="normalize",
            transform_name="normalize_activity",
            depends_on=("extract",),
            config={"a": {"y": 2, "z": 1}, "b": 2},
        )
    )

    assert left.fingerprint == right.fingerprint


def test_transform_fingerprint_changes_when_config_changes() -> None:
    base = WorkflowTransformSpec(
        step_id="normalize",
        transform_name="normalize_activity",
        config={"profile": "activity"},
    )
    changed = WorkflowTransformSpec(
        step_id="normalize",
        transform_name="normalize_activity",
        config={"profile": "assay"},
    )

    assert base.fingerprint != changed.fingerprint


def test_transform_fingerprint_normalizes_tuple_and_nested_sequence_values() -> None:
    left = WorkflowTransformSpec(
        step_id="normalize",
        transform_name="normalize_activity",
        config={
            "targets": ("b", "a"),
            "nested": ({"y": 2, "x": 1}, ["keep", {"b": 2, "a": 1}]),
        },
    )
    right = WorkflowTransformSpec(
        step_id="normalize",
        transform_name="normalize_activity",
        config={
            "targets": ["b", "a"],
            "nested": [{"x": 1, "y": 2}, ["keep", {"a": 1, "b": 2}]],
        },
    )

    assert left.fingerprint == right.fingerprint
