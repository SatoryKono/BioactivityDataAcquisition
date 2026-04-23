from __future__ import annotations

import asyncio
import sys
from types import ModuleType
from unittest import mock

from bioetl.composition import observability_api


def test_start_metrics_server_uses_metrics_service_start() -> None:
    metrics_service = mock.Mock()
    metrics_service.start.return_value = mock.Mock(success=True)

    with mock.patch.object(
        observability_api,
        "get_metrics_service",
        return_value=metrics_service,
    ) as mock_get_service:
        result = observability_api.start_metrics_server(
            port=9100,
            addr="127.0.0.1",
            fail_fast=True,
            retry_count=5,
            retry_delay=0.5,
        )

    assert result is True
    mock_get_service.assert_called_once_with()
    metrics_service.start.assert_called_once_with(
        port=9100,
        addr="127.0.0.1",
        fail_fast=True,
        retry_count=5,
        retry_delay=0.5,
    )


def test_start_metrics_server_overrides_logger_when_provided() -> None:
    metrics_service = mock.Mock()
    metrics_service.start.return_value = mock.Mock(success=True)
    logger = mock.Mock()

    with mock.patch.object(
        observability_api,
        "get_metrics_service",
        return_value=metrics_service,
    ):
        observability_api.start_metrics_server(logger=logger)

    assert metrics_service.logger is logger


def test_get_metrics_service_delegates_to_services_api() -> None:
    expected = mock.Mock()
    fake_services_api = ModuleType("bioetl.composition.services_api")
    mock_impl = mock.Mock(return_value=expected)
    fake_services_api.get_metrics_service = mock_impl
    with mock.patch.dict(
        sys.modules,
        {"bioetl.composition.services_api": fake_services_api},
    ):
        result = observability_api.get_metrics_service()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_push_metrics_to_gateway_uses_metrics_service_push() -> None:
    metrics_service = mock.Mock()
    metrics_service.push_to_gateway.return_value = mock.Mock(success=True)

    with mock.patch.object(
        observability_api,
        "get_metrics_service",
        return_value=metrics_service,
    ) as mock_get_service:
        result = observability_api.push_metrics_to_gateway(
            run_label="bioetl",
            pipeline_name="chembl_activity",
            run_type="incremental",
        )

    assert result is True
    mock_get_service.assert_called_once_with()
    metrics_service.push_to_gateway.assert_called_once_with(
        gateway=mock.ANY,
        run_label="bioetl",
        grouping_key={
            "pipeline": "chembl_activity",
            "run_type": "incremental",
        },
    )


def test_get_audit_service_delegates_to_services_api() -> None:
    expected = mock.Mock()
    fake_services_api = ModuleType("bioetl.composition.services_api")
    mock_impl = mock.Mock(return_value=expected)
    fake_services_api.get_audit_service = mock_impl
    with mock.patch.dict(
        sys.modules,
        {"bioetl.composition.services_api": fake_services_api},
    ):
        result = observability_api.get_audit_service()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_get_observability_workflow_service_delegates_to_services_api() -> None:
    expected = mock.Mock()
    fake_services_api = ModuleType("bioetl.composition.services_api")
    mock_impl = mock.Mock(return_value=expected)
    fake_services_api.get_observability_workflow_service = mock_impl
    with mock.patch.dict(
        sys.modules,
        {"bioetl.composition.services_api": fake_services_api},
    ):
        result = observability_api.get_observability_workflow_service()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_inspect_run_dossier_delegates_to_workflow_service() -> None:
    workflow_service = mock.AsyncMock()
    workflow_service.inspect_run_dossier.return_value = expected = mock.Mock()

    with mock.patch.object(
        observability_api,
        "get_observability_workflow_service",
        return_value=workflow_service,
    ) as mock_get_workflow:
        result = asyncio.run(
            observability_api.inspect_run_dossier("run-123", audit_limit=7)
        )

    assert result is expected
    mock_get_workflow.assert_called_once_with()
    workflow_service.inspect_run_dossier.assert_awaited_once_with(
        "run-123",
        audit_limit=7,
    )


def test_get_observability_diagnostics_bundle_builds_bundle() -> None:
    health_service = mock.Mock()
    checkpoint_service = mock.Mock()
    audit_service = mock.Mock()
    metrics_service = mock.Mock()
    quarantine_service = mock.Mock()
    run_manifest_service = mock.Mock()
    lineage_service = mock.Mock()
    workflow_service = mock.Mock()

    with (
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

    assert bundle.health_service is health_service
    assert bundle.checkpoint_service is checkpoint_service
    assert bundle.audit_service is audit_service
    assert bundle.metrics_service is metrics_service
    assert bundle.quarantine_service is quarantine_service
    assert bundle.run_manifest_service is run_manifest_service
    assert bundle.lineage_service is lineage_service
    assert bundle.workflow_service is workflow_service
    mock_health.assert_called_once_with()
    mock_checkpoint.assert_called_once_with()
    mock_audit.assert_called_once_with()
    mock_metrics.assert_called_once_with()
    mock_quarantine.assert_called_once_with()
    mock_manifest.assert_called_once_with()
    mock_lineage.assert_called_once_with()
    mock_workflow.assert_called_once_with()
