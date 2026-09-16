"""Focused tests for health-server composition dependency seams."""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from bioetl.interfaces.cli.commands.domains.health import (
    server_integration_deps as deps,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("data_root", [None, Path("data")])
def test_get_health_server_dependencies_delegates_optional_root(
    data_root: Path | None,
) -> None:
    sentinel = object()
    with patch(
        "bioetl.composition.health_service_access.get_health_server_dependencies",
        return_value=sentinel,
    ) as implementation:
        assert deps.get_health_server_dependencies(data_root=data_root) is sentinel
    if data_root is None:
        implementation.assert_called_once_with()
    else:
        implementation.assert_called_once_with(data_root=data_root)


@pytest.mark.parametrize("data_root", [None, Path("data")])
def test_get_health_server_quarantine_service_delegates_optional_root(
    data_root: Path | None,
) -> None:
    sentinel = object()
    with patch(
        "bioetl.composition.health_service_access.get_quarantine_service",
        return_value=sentinel,
    ) as implementation:
        assert (
            deps.get_health_server_quarantine_service(data_root=data_root) is sentinel
        )
    if data_root is None:
        implementation.assert_called_once_with()
    else:
        implementation.assert_called_once_with(data_root=data_root)


def test_get_quarantine_runtime_service_delegates_pipeline() -> None:
    sentinel = object()
    with patch(
        "bioetl.composition.health_service_access.get_quarantine_runtime_service",
        return_value=sentinel,
    ) as implementation:
        assert deps.get_quarantine_runtime_service("chembl_activity") is sentinel
    implementation.assert_called_once_with("chembl_activity")


def test_build_health_server_pycache_prefix_uses_temp_directory() -> None:
    assert deps.build_health_server_pycache_prefix() == Path(tempfile.gettempdir()) / (
        "bioetl-pycache"
    )


@pytest.mark.parametrize("data_root", [None, Path("data")])
def test_optional_quarantine_service_passes_optional_root(
    data_root: Path | None,
) -> None:
    sentinel = object()
    with patch.object(
        deps, "get_health_server_quarantine_service", return_value=sentinel
    ) as getter:
        assert (
            deps._get_optional_health_server_quarantine_service(data_root=data_root)
            is sentinel
        )
    if data_root is None:
        getter.assert_called_once_with()
    else:
        getter.assert_called_once_with(data_root=data_root)


def test_optional_quarantine_service_maps_typed_failure_to_none() -> None:
    with patch.object(
        deps,
        "get_health_server_quarantine_service",
        side_effect=ValueError("invalid configuration"),
    ):
        assert deps._get_optional_health_server_quarantine_service() is None


@pytest.mark.asyncio
async def test_close_health_server_resources_without_quarantine() -> None:
    checkpoint = SimpleNamespace(aclose=AsyncMock())
    await deps.close_health_server_resources(
        deps=SimpleNamespace(checkpoint_port=checkpoint), quarantine_service=None
    )
    checkpoint.aclose.assert_awaited_once()
