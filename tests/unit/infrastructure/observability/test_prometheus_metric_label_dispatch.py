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
    }
