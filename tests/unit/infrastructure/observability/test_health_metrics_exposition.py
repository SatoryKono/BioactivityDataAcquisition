"""Tests for health-server Prometheus exposition fallbacks."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from bioetl.infrastructure.observability.health_metrics_exposition import (
    HEALTH_SCRAPE_UP_EXPOSITION,
    HealthMetricsExpositionAdapter,
    build_health_server_metrics_exposition,
)

pytestmark = pytest.mark.unit


def test_health_metrics_exposition_uses_liveness_metric_for_empty_registry() -> None:
    with patch("prometheus_client.generate_latest", return_value=b""):
        assert build_health_server_metrics_exposition() == HEALTH_SCRAPE_UP_EXPOSITION


def test_health_metrics_exposition_fails_closed_on_registry_error() -> None:
    with patch(
        "prometheus_client.generate_latest", side_effect=RuntimeError("registry failed")
    ):
        assert build_health_server_metrics_exposition() == HEALTH_SCRAPE_UP_EXPOSITION


def test_health_metrics_exposition_appends_liveness_metric_to_registry_body() -> None:
    with patch("prometheus_client.generate_latest", return_value=b"existing_metric 2"):
        exposition = build_health_server_metrics_exposition()
    assert exposition.startswith("existing_metric 2\n")
    assert exposition.endswith(HEALTH_SCRAPE_UP_EXPOSITION)


def test_health_metrics_exposition_adapter_delegates_builder() -> None:
    with patch(
        "bioetl.infrastructure.observability.health_metrics_exposition.build_health_server_metrics_exposition",
        return_value="metric 1\n",
    ) as builder:
        assert HealthMetricsExpositionAdapter().build_exposition() == "metric 1\n"
    builder.assert_called_once_with()
