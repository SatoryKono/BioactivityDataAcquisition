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
"""Tests for Prometheus metric label dispatch normalization."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.observability.prometheus_metric_label_dispatch import (
    normalize_metric_dispatch_labels,
)

pytestmark = pytest.mark.unit


def test_metric_dispatch_normalizes_pipeline_label_contract_refs() -> None:
    labels = normalize_metric_dispatch_labels(
        "bioetl_pipeline_runs_total",
        {
            "pipeline": "chembl.activity",
            "run_type": "incremental",
            "status": "success",
        },
    )

    assert labels == {
        "pipeline": "chembl_activity",
        "run_type": "incremental",
        "status": "success",
    }


def test_metric_dispatch_normalizes_pipeline_label_after_group_normalizer() -> None:
    labels = normalize_metric_dispatch_labels(
        "bioetl_stage_records_total",
        {
            "pipeline": "chembl.activity",
            "run_type": "incremental",
            "stage": "silver",
        },
    )

    assert labels == {
        "pipeline": "chembl_activity",
        "run_type": "incremental",
        "stage": "silver",
        "outcome": "other",
    }


def test_metric_dispatch_stage_model_uses_bounded_defaults() -> None:
    """The dispatch snapshot owns the full published stage-model contract."""
    labels = normalize_metric_dispatch_labels(
        "bioetl_stage_records_total",
        {
            "pipeline": "chembl.activity",
            "run_type": "incremental",
            "stage": "unbounded-stage",
        },
    )

    assert labels == {
        "pipeline": "chembl_activity",
        "run_type": "incremental",
        "stage": "other",
        "outcome": "other",
    }


def test_metric_dispatch_canonicalizes_composite_pipeline_after_phase_normalizer() -> (
    None
):
    labels = normalize_metric_dispatch_labels(
        "bioetl_composite_phase_records_total",
        {
            "pipeline": "composite:target",
            "phase": "extract",
            "outcome": "success",
        },
    )

    assert labels == {
        "pipeline": "composite_target",
        "phase": "other",
        "outcome": "other",
    }
