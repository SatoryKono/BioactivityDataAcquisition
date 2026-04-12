"""Unit tests for preflight reporting helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.preflight.preflight_reporting import (
    record_preflight_metrics,
)
from bioetl.domain.types import HealthReport, PreflightReport


def _make_host(*, pipeline_name: str = "chembl_activity") -> SimpleNamespace:
    return SimpleNamespace(
        _config=SimpleNamespace(pipeline_name=pipeline_name),
        _context=SimpleNamespace(run_id=uuid4()),
        _metrics=MagicMock(),
    )


@pytest.mark.unit
def test_record_preflight_metrics_uses_only_pipeline_label_for_policy_gauge() -> None:
    """Preflight policy gauge must not emit high-cardinality run identifiers."""
    host = _make_host()
    report = PreflightReport(
        health_report=HealthReport(results=[]),
        medallion_policy_valid=True,
        config_errors=[],
    )

    record_preflight_metrics(host, report)

    host._metrics.set_gauge.assert_any_call(
        "bioetl_preflight_medallion_policy_valid",
        1.0,
        {"pipeline": "chembl_activity"},
    )


@pytest.mark.unit
def test_record_preflight_metrics_uses_only_pipeline_label_for_error_gauge() -> None:
    """Preflight error gauge must aggregate by pipeline instead of per-run labels."""
    host = _make_host(pipeline_name="pubmed_publication")
    report = PreflightReport(
        health_report=HealthReport(results=[]),
        medallion_policy_valid=False,
        config_errors=[
            MagicMock(),
            MagicMock(),
        ],
    )

    record_preflight_metrics(host, report)

    host._metrics.set_gauge.assert_any_call(
        "bioetl_preflight_config_errors_total",
        2.0,
        {"pipeline": "pubmed_publication"},
    )

    for call in host._metrics.set_gauge.call_args_list:
        labels = call.args[2]
        assert "run_id" not in labels
