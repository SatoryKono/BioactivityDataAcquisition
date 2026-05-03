"""Legacy lock runtime naming shim."""

from __future__ import annotations

__all__ = ["LockCoordinator", "LockCoordinatorCreateContext"]

from bioetl.application.core.lifecycle.lock_runtime_service import (
    LockRuntimeService,
    LockRuntimeServiceCreateContext,
)

LockCoordinator = LockRuntimeService
LockCoordinatorCreateContext = LockRuntimeServiceCreateContext
