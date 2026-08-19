"""Canonical observability QA context for dashboard URLs."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ops.observability.grafana.qa_context import (
    grafana_qa_query_params,
    load_observability_qa_context,
)

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[5]


def test_qa_context_is_chembl_backfill_scope() -> None:
    context = load_observability_qa_context(ROOT)
    assert context["schema_version"] == "observability_qa_context_v1"
    assert context["pipeline"] == "chembl_assay"
    assert context["run_type"] == "backfill"
    assert context["provider"] == "chembl"
    params = grafana_qa_query_params(ROOT)
    assert params["var-provider"] == "chembl"
    assert params["var-pipeline"] == "chembl_assay"
    assert params["from"] == "now-6h"
