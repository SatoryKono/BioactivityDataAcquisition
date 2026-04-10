from __future__ import annotations

from unittest import mock

import pytest

from bioetl.composition.bootstrap.runtime import (
    observability as composition_observability,
)
from bioetl.composition import observability_api as composition_observability_api
from bioetl.domain import exceptions as domain_exceptions
from bioetl.infrastructure import observability as infra_observability
from bioetl.infrastructure.observability import server as obs_server
from bioetl.interfaces import observability

# This module tests the observability interface.
# MetricsServerError is now defined in domain.exceptions and re-exported by all layers.
# interfaces.observability exposes start_metrics_server via composition entrypoints.


# Mock `_SERVER_STARTED` to isolate state among test cases.
@pytest.fixture(autouse=True)
def reset_server_started():
    """Reset the `_SERVER_STARTED` before each test."""
    obs_server._SERVER_STARTED = False  # Ensure isolation
    yield
    obs_server._SERVER_STARTED = False  # Cleanup


def test_start_metrics_server_success():
    """Verify metrics_server starts successfully via interface."""
    with mock.patch(
        "bioetl.infrastructure.observability.server.start_http_server"
    ) as mock_start:
        observability.start_metrics_server()
        mock_start.assert_called_once()


def test_start_metrics_server_failure():
    """Simulate server failure and verify graceful handling via interface.

    The server is designed to catch exceptions and return False (fail_fast=False by default)
    rather than raising exceptions, to allow pipelines to continue without metrics.
    """
    with mock.patch(
        "bioetl.infrastructure.observability.server.start_http_server",
        side_effect=RuntimeError("Failed"),
    ):
        # Interface should catch exceptions and return False for graceful degradation
        result = observability.start_metrics_server(port=8000, fail_fast=False)
        assert result is False


def test_start_metrics_server_fail_fast_propagation():
    """Verify that fail_fast=True propagates MetricsServerError via interface."""
    with mock.patch(
        "bioetl.infrastructure.observability.server.start_http_server",
        side_effect=RuntimeError("Failed"),
    ):
        with pytest.raises(domain_exceptions.MetricsServerError):
            observability.start_metrics_server(port=8000, fail_fast=True)


def test_start_metrics_server_default_arguments():
    """Verify that default arguments are correctly passed through the interface."""
    with mock.patch(
        "bioetl.composition.observability_api.start_metrics_server",
        return_value=True,
    ) as mock_impl:
        result = observability.start_metrics_server()

        assert result is True
        mock_impl.assert_called_once_with(
            port=8000,
            addr="0.0.0.0",
            fail_fast=False,
            retry_count=3,
            retry_delay=1.0,
            logger=None,
        )


def test_interface_re_exports_from_composition_observability_api():
    """Verify interface delegates start_metrics_server via composition API.

    interfaces/observability.py now exposes a thin wrapper over
    composition.observability_api.start_metrics_server, preserving the public API
    while removing the direct module-level composition import.
    """
    logger = mock.Mock()

    with mock.patch.object(
        composition_observability_api,
        "start_metrics_server",
        return_value=True,
    ) as mock_start_metrics_server:
        result = observability.start_metrics_server(
            port=9100,
            addr="127.0.0.1",
            fail_fast=True,
            retry_count=5,
            retry_delay=0.5,
            logger=logger,
        )

    assert result is True
    mock_start_metrics_server.assert_called_once_with(
        port=9100,
        addr="127.0.0.1",
        fail_fast=True,
        retry_count=5,
        retry_delay=0.5,
        logger=logger,
    )


def test_interface_exposes_metrics_server_error():
    """Verify MetricsServerError is exported from interface via domain.

    MetricsServerError is defined in domain.exceptions.critical and
    re-exported by all layers (infrastructure, composition, interfaces).
    """
    # All layers should reference the same exception class from domain
    assert observability.MetricsServerError is domain_exceptions.MetricsServerError
    assert (
        infra_observability.MetricsServerError is domain_exceptions.MetricsServerError
    )
    assert obs_server.MetricsServerError is domain_exceptions.MetricsServerError
    assert (
        composition_observability.MetricsServerError
        is domain_exceptions.MetricsServerError
    )


def test_get_metrics_service_delegates_to_composition_services_api() -> None:
    expected = mock.Mock()
    with mock.patch(
        "bioetl.composition.services_api.get_metrics_service",
        return_value=expected,
    ) as mock_impl:
        result = observability.get_metrics_service()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_get_health_service_delegates_to_composition_services_api() -> None:
    expected = mock.Mock()
    with mock.patch(
        "bioetl.composition.services_api.get_health_service",
        return_value=expected,
    ) as mock_impl:
        result = observability.get_health_service()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_get_quarantine_service_delegates_to_composition_services_api() -> None:
    expected = mock.Mock()
    with mock.patch(
        "bioetl.composition.services_api.get_quarantine_service",
        return_value=expected,
    ) as mock_impl:
        result = observability.get_quarantine_service()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_get_run_manifest_service_delegates_to_composition_services_api() -> None:
    expected = mock.Mock()
    with mock.patch(
        "bioetl.composition.services_api.get_run_manifest_service",
        return_value=expected,
    ) as mock_impl:
        result = observability.get_run_manifest_service()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_get_lineage_service_delegates_to_composition_services_api() -> None:
    expected = mock.Mock()
    with mock.patch(
        "bioetl.composition.services_api.get_lineage_service",
        return_value=expected,
    ) as mock_impl:
        result = observability.get_lineage_service()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_get_observability_diagnostics_bundle_builds_unified_bundle() -> None:
    health_service = mock.Mock()
    metrics_service = mock.Mock()
    quarantine_service = mock.Mock()
    run_manifest_service = mock.Mock()
    lineage_service = mock.Mock()

    with (
        mock.patch.object(
            observability,
            "get_health_service",
            return_value=health_service,
        ) as mock_health,
        mock.patch.object(
            observability,
            "get_metrics_service",
            return_value=metrics_service,
        ) as mock_metrics,
        mock.patch.object(
            observability,
            "get_quarantine_service",
            return_value=quarantine_service,
        ) as mock_quarantine,
        mock.patch.object(
            observability,
            "get_run_manifest_service",
            return_value=run_manifest_service,
        ) as mock_manifest,
        mock.patch.object(
            observability,
            "get_lineage_service",
            return_value=lineage_service,
        ) as mock_lineage,
    ):
        bundle = observability.get_observability_diagnostics_bundle()

    assert bundle.health_service is health_service
    assert bundle.metrics_service is metrics_service
    assert bundle.quarantine_service is quarantine_service
    assert bundle.run_manifest_service is run_manifest_service
    assert bundle.lineage_service is lineage_service
    mock_health.assert_called_once_with()
    mock_metrics.assert_called_once_with()
    mock_quarantine.assert_called_once_with()
    mock_manifest.assert_called_once_with()
    mock_lineage.assert_called_once_with()
