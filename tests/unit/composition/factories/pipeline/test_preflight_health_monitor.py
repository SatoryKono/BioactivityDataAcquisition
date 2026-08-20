# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for preflight provider-health composition wiring."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.pipeline import _preflight_health_monitor as module
from bioetl.infrastructure.adapters.http.health_monitor import ProviderHealthMonitor
from bioetl.infrastructure.control_plane.provider_health_evidence import (
    PersistingProviderHealthMonitor,
)


pytestmark = pytest.mark.unit


def test_build_preflight_health_monitor_wraps_when_store_available() -> None:
    store = MagicMock(name="FileProviderHealthEvidenceStore")
    metrics = MagicMock(name="MetricsPort")

    with patch.object(module, "_provider_health_evidence_store", return_value=store):
        monitor = module.build_preflight_health_monitor(metrics)

    assert isinstance(monitor, PersistingProviderHealthMonitor)
    assert monitor.store is store
    assert isinstance(monitor.inner, ProviderHealthMonitor)


def test_build_preflight_health_monitor_falls_back_when_store_missing() -> None:
    metrics = MagicMock(name="MetricsPort")

    with patch.object(module, "_provider_health_evidence_store", return_value=None):
        monitor = module.build_preflight_health_monitor(metrics)

    assert isinstance(monitor, ProviderHealthMonitor)


def test_rehydrate_provider_health_gauges_uses_persisted_store() -> None:
    store = MagicMock(name="FileProviderHealthEvidenceStore")
    metrics = MagicMock(name="MetricsPort")

    with (
        patch.object(module, "_provider_health_evidence_store", return_value=store),
        patch.object(
            module,
            "rehydrate_provider_health_evidence",
            return_value=3,
        ) as rehydrate,
    ):
        published = module.rehydrate_provider_health_gauges(metrics)

    assert published == 3
    rehydrate.assert_called_once()
    assert rehydrate.call_args.args[:2] == (metrics, store)
    assert "now" in rehydrate.call_args.kwargs


def test_rehydrate_provider_health_gauges_returns_zero_without_store() -> None:
    metrics = MagicMock(name="MetricsPort")

    with (
        patch.object(module, "_provider_health_evidence_store", return_value=None),
        patch.object(module, "rehydrate_provider_health_evidence") as rehydrate,
    ):
        published = module.rehydrate_provider_health_gauges(metrics)

    assert published == 0
    rehydrate.assert_not_called()


def test_provider_health_evidence_store_returns_none_on_settings_error() -> None:
    with patch.object(module, "get_settings", side_effect=RuntimeError("no settings")):
        assert module._provider_health_evidence_store() is None


def test_health_api_rehydrate_export_delegates_to_preflight_wiring() -> None:
    from bioetl.composition import health_api
    from bioetl.composition.factories.pipeline._preflight_health_monitor import (
        rehydrate_provider_health_gauges as impl,
    )

    health_api.__dict__.pop("rehydrate_provider_health_gauges", None)

    assert health_api.rehydrate_provider_health_gauges is impl
    assert "rehydrate_provider_health_gauges" in health_api.__all__
