"""Shared checkpoint runtime compatibility type aliases."""

from __future__ import annotations

from typing import Literal

CheckpointCompatibilityPolicy = Literal["observe", "soft_fail", "hard_fail"]
CheckpointCompatibilityDisposition = Literal[
    "observe_blocked_identity",
    "observe_loaded_degraded",
    "soft_fail_blocked",
    "hard_fail_raised",
]
CheckpointMissingContextDisposition = Literal[
    "missing_context_hard_fail_raised",
]

__all__ = [
    "CheckpointCompatibilityDisposition",
    "CheckpointCompatibilityPolicy",
    "CheckpointMissingContextDisposition",
]
