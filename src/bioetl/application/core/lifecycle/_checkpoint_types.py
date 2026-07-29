"""Private checkpoint typing helpers."""

from __future__ import annotations

from typing import Protocol

from bioetl.domain.types.checkpoint_compatibility_result import (
    CheckpointCompatibilityResult,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


class CheckpointCompatibilityService(Protocol):
    """Duck-typed contract for checkpoint compatibility validation."""

    def validate_checkpoint_compatibility(
        self,
        current_metadata: CheckpointMetadata,
        checkpoint_metadata: CheckpointMetadata,
    ) -> CheckpointCompatibilityResult: ...
