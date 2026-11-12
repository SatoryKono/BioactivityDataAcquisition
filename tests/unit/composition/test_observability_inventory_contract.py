"""Composition preserves metric drift evidence and the caller allowlist."""

from __future__ import annotations
from unittest.mock import Mock
import pytest
from bioetl.composition import observability_runtime as subject

pytestmark = pytest.mark.unit


def test_inventory_check_passes_same_report_and_allowlist(tmp_path, monkeypatch):
    report = {"unused_declared_metrics": ["retired", "unexpected"]}
    allowed = {"unused_declared_metrics": {"retired"}}
    collector = Mock(return_value=report)
    monkeypatch.setattr(subject, "collect_metric_inventory", collector)
    result, violations = subject.check_metric_inventory(tmp_path, allowed)
    assert result is report
    assert violations == {"unused_declared_metrics": ["unexpected"]}
    collector.assert_called_once_with(tmp_path)
