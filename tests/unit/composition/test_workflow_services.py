# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for workflow-specific composition service assembly."""

from __future__ import annotations

import pytest

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import sentinel

from bioetl.composition import _workflow_services


pytestmark = pytest.mark.unit


def test_workflow_composition_passes_configured_report_root(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        data_dir=tmp_path / "data", report_root=tmp_path / "reports"
    )
    monkeypatch.setattr(_workflow_services, "get_settings", lambda: settings)
    monkeypatch.setattr(
        _workflow_services, "_create_workflow_metrics", lambda _: sentinel.metrics
    )
    monkeypatch.setattr(
        _workflow_services,
        "build_workflow_transform_registry",
        lambda *_args, **_kwargs: {},
    )
    service = _workflow_services.get_workflow_runner_service(
        pipeline_runner_service_factory=lambda _: sentinel.pipeline_runner,
    )
    assert service.report_root == settings.report_root


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
        _workflow_services,
        "get_settings",
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


def test_system_clock_factory_returns_timezone_aware_now() -> None:
    """Workflow ledger timestamps must come from the canonical system clock."""
    assert _workflow_services._system_clock_now()().tzinfo is not None


def test_get_workflow_memory_lock_is_singleton_under_concurrency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent first callers must share one lazily created MemoryLock."""
    import threading

    created: list[object] = []

    def _memory_lock_factory() -> object:
        lock = object()
        created.append(lock)
        return lock

    monkeypatch.setattr(
        "bioetl.infrastructure.locking.MemoryLock",
        _memory_lock_factory,
    )
    _workflow_services._workflow_memory_lock = None

    locks: list[object] = []

    def _worker() -> None:
        locks.append(_workflow_services._get_workflow_memory_lock())

    threads = [threading.Thread(target=_worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(created) == 1
    assert len({id(lock) for lock in locks}) == 1
