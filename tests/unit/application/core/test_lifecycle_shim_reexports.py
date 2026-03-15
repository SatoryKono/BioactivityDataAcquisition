"""Unit tests for application.core lifecycle compatibility re-exports."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_checkpoint_manager_reexports() -> None:
    """Legacy checkpoint_manager shim re-exports canonical lifecycle symbols."""
    from bioetl.application.core.checkpoint_manager import (
        CheckpointManager,
        CheckpointManagerService,
    )
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointManager as CanonicalCheckpointManager,
    )
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointManagerService as CanonicalCheckpointManagerService,
    )

    assert CheckpointManager is CanonicalCheckpointManager
    assert CheckpointManagerService is CanonicalCheckpointManagerService


@pytest.mark.unit
def test_cleanup_service_reexports() -> None:
    """Legacy cleanup_service shim re-exports canonical lifecycle symbols."""
    from bioetl.application.core.cleanup_service import (
        CleanupPreview,
        CleanupResult,
        CleanupService,
        LayerInfo,
    )
    from bioetl.application.core.lifecycle.cleanup_service import (
        CleanupPreview as CanonicalCleanupPreview,
    )
    from bioetl.application.core.lifecycle.cleanup_service import (
        CleanupResult as CanonicalCleanupResult,
    )
    from bioetl.application.core.lifecycle.cleanup_service import (
        CleanupService as CanonicalCleanupService,
    )
    from bioetl.application.core.lifecycle.cleanup_service import (
        LayerInfo as CanonicalLayerInfo,
    )

    assert CleanupPreview is CanonicalCleanupPreview
    assert CleanupResult is CanonicalCleanupResult
    assert CleanupService is CanonicalCleanupService
    assert LayerInfo is CanonicalLayerInfo


@pytest.mark.unit
def test_heartbeat_reexports() -> None:
    """Legacy heartbeat shim re-exports canonical lifecycle symbol."""
    from bioetl.application.core.heartbeat import HeartbeatTask
    from bioetl.application.core.lifecycle.heartbeat import (
        HeartbeatTask as CanonicalHeartbeatTask,
    )

    assert HeartbeatTask is CanonicalHeartbeatTask


@pytest.mark.unit
def test_lock_manager_reexports() -> None:
    """Legacy lock_manager shim re-exports canonical lifecycle symbol."""
    from bioetl.application.core.lifecycle.lock_manager import (
        LockCoordinator as CanonicalLockCoordinator,
    )
    from bioetl.application.core.lock_manager import LockCoordinator

    assert LockCoordinator is CanonicalLockCoordinator


@pytest.mark.unit
def test_shutdown_reexports() -> None:
    """Legacy shutdown shim re-exports canonical lifecycle symbols."""
    from bioetl.application.core.lifecycle.shutdown import (
        PipelineShutdownError as CanonicalPipelineShutdownError,
    )
    from bioetl.application.core.lifecycle.shutdown import (
        ShutdownReason as CanonicalShutdownReason,
    )
    from bioetl.application.core.lifecycle.shutdown import (
        ShutdownService as CanonicalShutdownService,
    )
    from bioetl.application.core.lifecycle.shutdown import (
        ShutdownSignal as CanonicalShutdownSignal,
    )
    from bioetl.application.core.shutdown import (
        PipelineShutdownError,
        ShutdownReason,
        ShutdownService,
        ShutdownSignal,
    )

    assert PipelineShutdownError is CanonicalPipelineShutdownError
    assert ShutdownReason is CanonicalShutdownReason
    assert ShutdownService is CanonicalShutdownService
    assert ShutdownSignal is CanonicalShutdownSignal
