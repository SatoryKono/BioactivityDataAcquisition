"""Unit tests for the legacy services_api compatibility umbrella."""

from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, patch

import pytest

from bioetl.composition.registry_api import PipelineRegistry


pytestmark = pytest.mark.unit


def _services_api():
    return importlib.import_module("bioetl.composition.services_api")


@pytest.mark.parametrize(
    ("attr_name", "patch_target"),
    [
        (
            "get_adr_service",
            "bioetl.composition.control_plane_api.get_adr_service",
        ),
        (
            "get_audit_service",
            "bioetl.composition.observability_api.get_audit_service",
        ),
        (
            "get_bronze_cleanup_service",
            "bioetl.composition.maintenance_api.get_bronze_cleanup_service",
        ),
        (
            "get_checkpoint_service",
            "bioetl.composition.observability_api.get_checkpoint_service",
        ),
        (
            "get_config_service",
            "bioetl.composition.control_plane_api.get_config_service",
        ),
        (
            "get_contract_migration_service",
            "bioetl.composition.maintenance_api.get_contract_migration_service",
        ),
        (
            "get_export_service",
            "bioetl.composition.control_plane_api.get_export_service",
        ),
        (
            "get_forensic_run_diff_service",
            "bioetl.composition.control_plane_api.get_forensic_run_diff_service",
        ),
        (
            "get_health_server_dependencies",
            "bioetl.composition.health_api.get_health_server_dependencies",
        ),
        (
            "get_health_service",
            "bioetl.composition.health_api.get_health_service",
        ),
        (
            "get_lineage_service",
            "bioetl.composition.control_plane_api.get_lineage_service",
        ),
        (
            "get_lock_service",
            "bioetl.composition.control_plane_api.get_lock_service",
        ),
        (
            "get_metrics_service",
            "bioetl.composition.observability_api.get_metrics_service",
        ),
        (
            "get_observability_workflow_service",
            "bioetl.composition.observability_api.get_observability_workflow_service",
        ),
        (
            "get_quarantine_port",
            "bioetl.composition.health_api.get_quarantine_port",
        ),
        (
            "get_quarantine_service",
            "bioetl.composition.health_api.get_quarantine_service",
        ),
        (
            "get_run_manifest_service",
            "bioetl.composition.control_plane_api.get_run_manifest_service",
        ),
        (
            "get_vacuum_service",
            "bioetl.composition.maintenance_api.get_vacuum_service",
        ),
    ],
)
def test_zero_arg_service_getters_delegate_to_narrow_public_facades(
    attr_name: str,
    patch_target: str,
) -> None:
    expected = object()

    with patch(patch_target, return_value=expected) as mock_impl:
        result = getattr(_services_api(), attr_name)()

    mock_impl.assert_called_once_with()
    assert result is expected


def test_get_pipeline_runner_service_delegates_to_execution_api() -> None:
    expected = object()
    registry = PipelineRegistry()

    with patch(
        "bioetl.composition.execution_api.get_pipeline_runner_service",
        return_value=expected,
    ) as mock_impl:
        result = _services_api().get_pipeline_runner_service(registry=registry)

    mock_impl.assert_called_once_with(registry=registry)
    assert result is expected


def test_get_workflow_execution_service_delegates_to_control_plane_api() -> None:
    expected = object()
    registry = PipelineRegistry()

    with patch(
        "bioetl.composition.control_plane_api.get_workflow_execution_service",
        return_value=expected,
    ) as mock_impl:
        result = _services_api().get_workflow_execution_service(registry=registry)

    mock_impl.assert_called_once_with(registry=registry)
    assert result is expected


def test_get_workflow_runner_service_delegates_to_control_plane_api() -> None:
    expected = object()
    registry = PipelineRegistry()

    with patch(
        "bioetl.composition.control_plane_api.get_workflow_runner_service",
        return_value=expected,
    ) as mock_impl:
        result = _services_api().get_workflow_runner_service(registry=registry)

    mock_impl.assert_called_once_with(registry=registry)
    assert result is expected


def test_get_workflow_inspection_service_delegates_to_control_plane_api() -> None:
    expected = object()

    with patch(
        "bioetl.composition.control_plane_api.get_workflow_inspection_service",
        return_value=expected,
    ) as mock_impl:
        result = _services_api().get_workflow_inspection_service()

    mock_impl.assert_called_once_with()
    assert result is expected


def test_load_workflow_config_delegates_to_control_plane_api() -> None:
    expected = object()

    with patch(
        "bioetl.composition.control_plane_api.load_workflow_config",
        return_value=expected,
    ) as mock_impl:
        result = _services_api().load_workflow_config("nightly")

    mock_impl.assert_called_once_with("nightly")
    assert result is expected


@pytest.mark.asyncio
async def test_cleanup_bronze_delegates_to_maintenance_api() -> None:
    expected = object()
    mock_impl = AsyncMock(return_value=expected)

    with patch("bioetl.composition.maintenance_api.cleanup_bronze", mock_impl):
        result = await _services_api().cleanup_bronze(
            retention_days=30,
            dry_run=True,
        )

    mock_impl.assert_awaited_once_with(retention_days=30, dry_run=True)
    assert result is expected


@pytest.mark.asyncio
async def test_cleanup_bronze_preserves_default_arguments() -> None:
    mock_impl = AsyncMock(return_value=object())

    with patch("bioetl.composition.maintenance_api.cleanup_bronze", mock_impl):
        await _services_api().cleanup_bronze()

    mock_impl.assert_awaited_once_with()
