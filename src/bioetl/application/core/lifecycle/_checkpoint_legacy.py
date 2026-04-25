"""Legacy compatibility alias for CheckpointManagerService."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


class CheckpointManager:
    """Deprecated compatibility alias retained for legacy constructor calls."""

    @property
    def current_metadata(self) -> CheckpointMetadata | None:
        raise NotImplementedError

    def __new__(
        cls,
        *args: object,
        **kwargs: object,
    ) -> object:
        from bioetl.application.core.lifecycle.checkpoint_manager import (
            CheckpointManagerService,
        )

        warnings.warn(
            "CheckpointManager is deprecated and will be removed in v2.0. "
            "Use CheckpointManagerService instead.",
            DeprecationWarning,
            stacklevel=3,
        )
        return CheckpointManagerService(*args, **kwargs)

    async def load_checkpoint(
        self,
        current_metadata: CheckpointMetadata | None = None,
    ) -> CheckpointMetadata | dict[str, object] | None:
        raise NotImplementedError

    async def save_checkpoint(self, metadata: CheckpointMetadata | int) -> None:
        raise NotImplementedError

    async def delete_checkpoint(self) -> None:
        raise NotImplementedError

    async def list_all(self) -> list[str]:
        raise NotImplementedError
