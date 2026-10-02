"""Disabled optional monitoring must not perform gateway I/O."""

import pytest
from types import SimpleNamespace
from unittest.mock import Mock

from bioetl.composition import observability_runtime


pytestmark = pytest.mark.unit


def test_disabled_metrics_skip_gateway_and_integrity_publication(monkeypatch):
    settings = SimpleNamespace(
        observability=SimpleNamespace(metrics_enabled=False),
        pushgateway_url="localhost:9091",
    )
    monkeypatch.setattr(
        observability_runtime._config_access, "get_settings", lambda: settings
    )
    publisher = Mock(side_effect=AssertionError("publication must remain disabled"))
    monkeypatch.setattr(observability_runtime, "bootstrap_metrics_service", publisher)
    monkeypatch.setattr(observability_runtime, "get_metrics_service", publisher)
    monkeypatch.setattr(observability_runtime, "_ensure_publication_seeds", publisher)
    assert observability_runtime.push_metrics_to_gateway(workflow_name="test") is False
    assert observability_runtime.push_metrics_to_gateway(pipeline_name="test") is False
    publisher.assert_not_called()
