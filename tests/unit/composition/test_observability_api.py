from __future__ import annotations

import pytest

import asyncio
import sys
from datetime import UTC, datetime
from types import ModuleType, SimpleNamespace
from unittest import mock

from bioetl.composition import observability_api


pytestmark = pytest.mark.unit


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


def test_start_metrics_server_returns_false_or_raises_on_failed_start() -> None:
    metrics_service = mock.Mock()
    metrics_service.start.return_value = mock.Mock(success=False, error="bind failed")

    with mock.patch.object(
        observability_api,
        "get_metrics_service",
        return_value=metrics_service,
    ):
        assert observability_api.start_metrics_server(fail_fast=False) is False
        with pytest.raises(observability_api.MetricsServerError, match="bind failed"):
            observability_api.start_metrics_server(port=9200, fail_fast=True)


def test_get_metrics_service_delegates_to_internal_services_owner() -> None:
    expected = mock.Mock()
    fake_services = ModuleType("bioetl.composition._services")
    mock_impl = mock.Mock(return_value=expected)
    fake_services.get_metrics_service = mock_impl
    with mock.patch.dict(
        sys.modules,
        {"bioetl.composition._services": fake_services},
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
        metric_names=None,
    )


def test_push_metrics_to_gateway_does_not_bootstrap_fallback_logger() -> None:
    metrics_service = mock.Mock()
    metrics_service.logger = mock.sentinel.logger
    metrics_service.push_to_gateway.return_value = mock.Mock(success=True)

    with mock.patch.object(
        observability_api,
        "get_metrics_service",
        return_value=metrics_service,
    ):
        result = observability_api.push_metrics_to_gateway(
            run_label="bioetl",
            pipeline_name="chembl_activity",
        )

    assert result is True
    assert metrics_service.logger is mock.sentinel.logger


def test_push_metrics_to_gateway_applies_extra_grouping_metric_names_and_logger() -> None:
    metrics_service = mock.Mock()
    metrics_service.push_to_gateway.return_value = mock.Mock(success=True)
    settings = SimpleNamespace(pushgateway_url="pushgateway:9091")
    logger = mock.Mock()

    with (
        mock.patch(
            "bioetl.composition.runtime_builders.config_access.get_settings",
            return_value=settings,
        ),
        mock.patch.object(
            observability_api,
            "get_metrics_service",
            return_value=metrics_service,
        ),
    ):
        result = observability_api.push_metrics_to_gateway(
            run_label="bioetl",
            pipeline_name="chembl_activity",
            run_type="full",
            grouping_key_extra={"run_id": "run-1"},
            metric_names=("bioetl_rows_total",),
            logger=logger,
        )

    assert result is True
    assert metrics_service.logger is logger
    metrics_service.push_to_gateway.assert_called_once_with(
        gateway="pushgateway:9091",
        run_label="bioetl",
        grouping_key={
            "pipeline": "chembl_activity",
            "run_type": "full",
            "run_id": "run-1",
        },
        metric_names=("bioetl_rows_total",),
    )


def test_delete_metrics_from_gateway_uses_metrics_service_delete() -> None:
    metrics_service = mock.Mock()
    metrics_service.delete_from_gateway.return_value = mock.Mock(success=True)

    with mock.patch.object(
        observability_api,
        "get_metrics_service",
        return_value=metrics_service,
    ) as mock_get_service:
        result = observability_api.delete_metrics_from_gateway(
            run_label="bioetl",
            pipeline_name="chembl_activity",
            run_type="incremental",
        )

    assert result is True
    mock_get_service.assert_called_once_with()
    metrics_service.delete_from_gateway.assert_called_once_with(
        gateway=mock.ANY,
        run_label="bioetl",
        grouping_key={
            "pipeline": "chembl_activity",
            "run_type": "incremental",
        },
    )


def test_delete_metrics_from_gateway_does_not_bootstrap_fallback_logger() -> None:
    metrics_service = mock.Mock()
    metrics_service.logger = mock.sentinel.logger
    metrics_service.delete_from_gateway.return_value = mock.Mock(success=True)

    with mock.patch.object(
        observability_api,
        "get_metrics_service",
        return_value=metrics_service,
    ):
        result = observability_api.delete_metrics_from_gateway(
            run_label="bioetl",
            pipeline_name="chembl_activity",
        )

    assert result is True
    assert metrics_service.logger is mock.sentinel.logger


def test_delete_metrics_from_gateway_overrides_logger_and_uses_configured_gateway() -> None:
    metrics_service = mock.Mock()
    metrics_service.delete_from_gateway.return_value = mock.Mock(success=False)
    logger = mock.Mock()

    with (
        mock.patch(
            "bioetl.composition.runtime_builders.config_access.get_settings",
            return_value=SimpleNamespace(pushgateway_url="pushgateway:9091"),
        ),
        mock.patch.object(
            observability_api,
            "get_metrics_service",
            return_value=metrics_service,
        ),
    ):
        result = observability_api.delete_metrics_from_gateway(
            run_label="bioetl",
            run_type="incremental",
            logger=logger,
        )

    assert result is False
    assert metrics_service.logger is logger
    metrics_service.delete_from_gateway.assert_called_once_with(
        gateway="pushgateway:9091",
        run_label="bioetl",
        grouping_key={"run_type": "incremental"},
    )


def test_get_audit_service_delegates_to_internal_services_owner() -> None:
    expected = mock.Mock()
    fake_services = ModuleType("bioetl.composition._services")
    mock_impl = mock.Mock(return_value=expected)
    fake_services.get_audit_service = mock_impl
    with mock.patch.dict(
        sys.modules,
        {"bioetl.composition._services": fake_services},
    ):
        result = observability_api.get_audit_service()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_get_observability_workflow_service_delegates_to_internal_services_owner() -> (
    None
):
    expected = mock.Mock()
    fake_services = ModuleType("bioetl.composition._services")
    mock_impl = mock.Mock(return_value=expected)
    fake_services.get_observability_workflow_service = mock_impl
    with mock.patch.dict(
        sys.modules,
        {"bioetl.composition._services": fake_services},
    ):
        result = observability_api.get_observability_workflow_service()

    assert result is expected
    mock_impl.assert_called_once_with()


def test_remaining_service_delegates_use_internal_services_owner() -> None:
    fake_services = ModuleType("bioetl.composition._services")
    delegates = {
        "get_checkpoint_service": observability_api.get_checkpoint_service,
        "get_health_service": observability_api.get_health_service,
        "get_quarantine_service": observability_api.get_quarantine_service,
        "get_run_manifest_service": observability_api.get_run_manifest_service,
        "get_lineage_service": observability_api.get_lineage_service,
    }
    mocks: dict[str, mock.Mock] = {}
    for name in delegates:
        mocks[name] = mock.Mock(return_value=f"{name}:result")
        setattr(fake_services, name, mocks[name])

    with mock.patch.dict(
        sys.modules,
        {"bioetl.composition._services": fake_services},
    ):
        for name, fn in delegates.items():
            assert fn() == f"{name}:result"
            mocks[name].assert_called_once_with()


def test_get_metrics_operator_profile_reports_enabled_and_disabled_modes() -> None:
    metrics_service = mock.Mock()
    started_at = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)
    metrics_service.get_status.return_value = SimpleNamespace(
        running=True,
        port=9101,
        started_at=started_at,
    )
    enabled_settings = SimpleNamespace(
        metrics_port=8000,
        metrics_addr="127.0.0.1",
        pushgateway_url="",
        observability=SimpleNamespace(
            metrics_enabled=True,
            metrics_server_enabled=True,
            tracing_enabled=True,
            audit_enabled=False,
        ),
    )

    with (
        mock.patch(
            "bioetl.composition.runtime_builders.config_access.get_settings",
            return_value=enabled_settings,
        ),
        mock.patch.object(
            observability_api,
            "get_metrics_service",
            return_value=metrics_service,
        ),
    ):
        profile = observability_api.get_metrics_operator_profile()

    assert profile.metrics_endpoint == "http://127.0.0.1:9101/metrics"
    assert profile.metrics_server_mode == "auto_managed_during_pipeline_runs"
    assert profile.pushgateway_mode == "best_effort_on_run_completion"
    assert profile.pushgateway_gateway == "localhost:9091"
    assert profile.to_dict()["metrics_started_at"] == started_at.isoformat()

    metrics_service.get_status.return_value = SimpleNamespace(
        running=False,
        port=None,
        started_at=None,
    )
    disabled_settings = SimpleNamespace(
        metrics_port=8000,
        metrics_addr="0.0.0.0",
        pushgateway_url="pushgateway:9091",
        observability=SimpleNamespace(
            metrics_enabled=False,
            metrics_server_enabled=False,
            tracing_enabled=False,
            audit_enabled=True,
        ),
    )

    with (
        mock.patch(
            "bioetl.composition.runtime_builders.config_access.get_settings",
            return_value=disabled_settings,
        ),
        mock.patch.object(
            observability_api,
            "get_metrics_service",
            return_value=metrics_service,
        ),
    ):
        disabled_profile = observability_api.get_metrics_operator_profile()

    assert disabled_profile.metrics_endpoint is None
    assert disabled_profile.metrics_server_mode == "disabled"
    assert disabled_profile.pushgateway_mode == "disabled"
    assert disabled_profile.pushgateway_gateway == "pushgateway:9091"


def test_inspect_run_dossier_delegates_to_workflow_service() -> None:
    workflow_service = mock.AsyncMock()
    workflow_service.inspect_run_dossier.return_value = expected = mock.Mock()

    with mock.patch.object(
        observability_api,
        "get_observability_workflow_service",
        return_value=workflow_service,
    ) as mock_get_workflow:
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
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
