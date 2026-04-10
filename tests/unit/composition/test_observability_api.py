from __future__ import annotations

from unittest import mock

from bioetl.composition import observability_api


def test_get_metrics_service_delegates_to_services_api() -> None:
    expected = mock.Mock()
    with mock.patch(
        "bioetl.composition.services_api.get_metrics_service",
        return_value=expected,
    ) as mock_impl:
        result = observability_api.get_metrics_service()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_get_audit_service_delegates_to_services_api() -> None:
    expected = mock.Mock()
    with mock.patch(
        "bioetl.composition.services_api.get_audit_service",
        return_value=expected,
    ) as mock_impl:
        result = observability_api.get_audit_service()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_get_observability_workflow_service_delegates_to_services_api() -> None:
    expected = mock.Mock()
    with mock.patch(
        "bioetl.composition.services_api.get_observability_workflow_service",
        return_value=expected,
    ) as mock_impl:
        result = observability_api.get_observability_workflow_service()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_get_observability_diagnostics_bundle_builds_bundle() -> None:
    audit_service = mock.Mock()
    health_service = mock.Mock()
    checkpoint_service = mock.Mock()
    audit_service = mock.Mock()
    metrics_service = mock.Mock()
    workflow_service = mock.Mock()
    quarantine_service = mock.Mock()
    run_manifest_service = mock.Mock()
    lineage_service = mock.Mock()
    workflow_service = mock.Mock()

    with (
        mock.patch.object(
            observability_api,
            "get_audit_service",
            return_value=audit_service,
        ) as mock_audit,
        mock.patch.object(
            observability_api,
            "get_health_service",
            return_value=health_service,
        ) as mock_health,
        mock.patch.object(
            observability_api,
            "get_checkpoint_service",
            return_value=checkpoint_service,
        ) as mock_checkpoint,
        mock.patch.object(
            observability_api,
            "get_audit_service",
            return_value=audit_service,
        ) as mock_audit,
        mock.patch.object(
            observability_api,
            "get_metrics_service",
            return_value=metrics_service,
        ) as mock_metrics,
        mock.patch.object(
            observability_api,
            "get_observability_workflow_service",
            return_value=workflow_service,
        ) as mock_workflow,
        mock.patch.object(
            observability_api,
            "get_quarantine_service",
            return_value=quarantine_service,
        ) as mock_quarantine,
        mock.patch.object(
            observability_api,
            "get_run_manifest_service",
            return_value=run_manifest_service,
        ) as mock_manifest,
        mock.patch.object(
            observability_api,
            "get_lineage_service",
            return_value=lineage_service,
        ) as mock_lineage,
        mock.patch.object(
            observability_api,
            "get_observability_workflow_service",
            return_value=workflow_service,
        ) as mock_workflow,
    ):
        bundle = observability_api.get_observability_diagnostics_bundle()

    assert bundle.audit_service is audit_service
    assert bundle.health_service is health_service
    assert bundle.checkpoint_service is checkpoint_service
    assert bundle.audit_service is audit_service
    assert bundle.metrics_service is metrics_service
    assert bundle.workflow_service is workflow_service
    assert bundle.quarantine_service is quarantine_service
    assert bundle.run_manifest_service is run_manifest_service
    assert bundle.lineage_service is lineage_service
from __future__ import annotations

from unittest import mock

from bioetl.composition import observability_api


def test_get_metrics_service_delegates_to_services_api() -> None:
    expected = mock.Mock()
    with mock.patch(
        "bioetl.composition.services_api.get_metrics_service",
        return_value=expected,
    ) as mock_impl:
        result = observability_api.get_metrics_service()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_get_audit_service_delegates_to_services_api() -> None:
    expected = mock.Mock()
    with mock.patch(
        "bioetl.composition.services_api.get_audit_service",
        return_value=expected,
    ) as mock_impl:
        result = observability_api.get_audit_service()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_get_observability_workflow_service_delegates_to_services_api() -> None:
    expected = mock.Mock()
    with mock.patch(
        "bioetl.composition.services_api.get_observability_workflow_service",
        return_value=expected,
    ) as mock_impl:
        result = observability_api.get_observability_workflow_service()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_get_observability_diagnostics_bundle_builds_bundle() -> None:
    audit_service = mock.Mock()
    health_service = mock.Mock()
    checkpoint_service = mock.Mock()
    metrics_service = mock.Mock()
    workflow_service = mock.Mock()
    quarantine_service = mock.Mock()
    run_manifest_service = mock.Mock()
    lineage_service = mock.Mock()

    with (
        mock.patch.object(
            observability_api,
            "get_audit_service",
            return_value=audit_service,
        ) as mock_audit,
        mock.patch.object(
            observability_api,
            "get_health_service",
            return_value=health_service,
        ) as mock_health,
        mock.patch.object(
            observability_api,
            "get_checkpoint_service",
            return_value=checkpoint_service,
        ) as mock_checkpoint,
        mock.patch.object(
            observability_api,
            "get_metrics_service",
            return_value=metrics_service,
        ) as mock_metrics,
        mock.patch.object(
            observability_api,
            "get_observability_workflow_service",
            return_value=workflow_service,
        ) as mock_workflow,
        mock.patch.object(
            observability_api,
            "get_quarantine_service",
            return_value=quarantine_service,
        ) as mock_quarantine,
        mock.patch.object(
            observability_api,
            "get_run_manifest_service",
            return_value=run_manifest_service,
        ) as mock_manifest,
        mock.patch.object(
            observability_api,
            "get_lineage_service",
            return_value=lineage_service,
        ) as mock_lineage,
    ):
        bundle = observability_api.get_observability_diagnostics_bundle()

    assert bundle.audit_service is audit_service
    assert bundle.health_service is health_service
    assert bundle.checkpoint_service is checkpoint_service
    assert bundle.metrics_service is metrics_service
    assert bundle.workflow_service is workflow_service
    assert bundle.quarantine_service is quarantine_service
    assert bundle.run_manifest_service is run_manifest_service
    assert bundle.lineage_service is lineage_service
    mock_audit.assert_called_once_with()
    mock_health.assert_called_once_with()
    mock_checkpoint.assert_called_once_with()
    mock_metrics.assert_called_once_with()
    mock_workflow.assert_called_once_with()
    mock_quarantine.assert_called_once_with()
    mock_manifest.assert_called_once_with()
    mock_lineage.assert_called_once_with()
    mock_health.assert_called_once_with()
    mock_checkpoint.assert_called_once_with()
    mock_audit.assert_called_once_with()
    mock_metrics.assert_called_once_with()
    mock_workflow.assert_called_once_with()
    mock_quarantine.assert_called_once_with()
    mock_manifest.assert_called_once_with()
    mock_lineage.assert_called_once_with()
    mock_workflow.assert_called_once_with()
