"""Legacy compatibility alias for CheckpointManagerService."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointManagerService as _CheckpointManagerBase,
    )
    from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
else:
    _CheckpointManagerBase = object


class CheckpointManager(_CheckpointManagerBase):
    """Deprecated compatibility alias retained for legacy constructor calls."""

    @property
    def current_metadata(self) -> CheckpointMetadata | None:
        raise NotImplementedError

    def __new__(
        cls,
        *args: object,
        **kwargs: object,
    ) -> CheckpointManager:
        from bioetl.application.core.lifecycle.checkpoint_manager import (
            CheckpointManagerService,
        )

        warnings.warn(
            "CheckpointManager is deprecated and will be removed in v2.0. "
            "Use CheckpointManagerService instead.",
            DeprecationWarning,
            stacklevel=3,
        )
        return cast(
            CheckpointManager,
            CheckpointManagerService(
                *cast(tuple[Any, ...], args), **cast(dict[str, Any], kwargs)
            ),
        )

    async def load_checkpoint(
        self,
        current_metadata: CheckpointMetadata | None = None,
    ) -> CheckpointMetadata | None:
        raise NotImplementedError

    async def save_checkpoint(self, metadata: CheckpointMetadata | int) -> None:
        raise NotImplementedError

    async def delete_checkpoint(self) -> None:
        raise NotImplementedError

    async def list_all(self) -> list[str]:
        raise NotImplementedError
