"""Internal exceptions facade for critical application errors."""

from __future__ import annotations

from bioetl.domain.exceptions.internal_auth import AuthFailureError
from bioetl.domain.exceptions.internal_data import (
    CheckpointConflictError,
    MergeConflictError,
)
from bioetl.domain.exceptions.internal_lock import LockAcquisitionError, LockLostError
from bioetl.domain.exceptions.internal_state import (
    InvalidStateError,
    PolicyViolationError,
)
from bioetl.domain.exceptions.internal_system import (
    MetricsServerError,
    RunnerAlreadyExecutedError,
)

__all__ = [
    "AuthFailureError",
    "CheckpointConflictError",
    "InvalidStateError",
    "LockAcquisitionError",
    "LockLostError",
    "MergeConflictError",
    "MetricsServerError",
    "PolicyViolationError",
    "RunnerAlreadyExecutedError",
]
