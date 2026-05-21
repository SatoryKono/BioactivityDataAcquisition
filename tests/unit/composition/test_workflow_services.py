"""Unit tests for workflow-specific composition service assembly."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import sentinel

from bioetl.composition import _workflow_services


def test_get_workflow_execution_service_injects_real_manifest_clock(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Composition must not build workflow manifests with the epoch sentinel."""

    monkeypatch.setattr(
        _workflow_services,
        "get_workflow_runner_service",
        lambda registry=None: sentinel.workflow_runner,
    )
    monkeypatch.setattr(
        "bioetl.composition.factories.services.port_factories.create_metrics",
        lambda settings: sentinel.metrics,
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.config.get_settings",
        lambda: SimpleNamespace(data_dir=tmp_path),
    )

    service = _workflow_services.get_workflow_execution_service()

    assert service.workflow_runner is sentinel.workflow_runner
    created_at = service.manifest_service._resolve_created_at()
    assert isinstance(created_at, datetime)
    assert created_at.tzinfo is UTC
    assert service.manifest_service.manifest_port.base_path == (
        tmp_path / "output" / "control" / "workflow_manifest"
    )
    assert service.workflow_state_port.base_path == (
        tmp_path / "output" / "control" / "workflow_state"
    )
