"""Runtime metric diagnostics preserve collector and policy results."""

from __future__ import annotations

from unittest.mock import Mock
import pytest
from bioetl.composition import observability_runtime as subject

pytestmark = pytest.mark.unit


def test_metric_inventory_runtime_checks_the_collected_report_with_explicit_allowlist(
    monkeypatch, tmp_path
):
    report = {"declared_metrics": ["bioetl_example_total"]}
    violations = {"runtime_without_registry": ["bioetl_unknown_total"]}
    collect = Mock(return_value=report)
    validate = Mock(return_value=violations)
    monkeypatch.setattr(subject, "collect_metric_inventory", collect)
    monkeypatch.setattr(subject, "validate_metric_inventory", validate)
    allowed = {"runtime_without_registry": set()}
    assert subject.check_metric_inventory(tmp_path, allowed) == (report, violations)
    collect.assert_called_once_with(tmp_path)
    validate.assert_called_once_with(report, allowlist=allowed)
