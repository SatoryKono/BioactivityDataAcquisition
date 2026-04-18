"""Legacy compatibility alias for CheckpointManagerService."""

from __future__ import annotations

import warnings

class CheckpointManager:
    """Deprecated compatibility alias retained for legacy constructor calls."""

    def __new__(cls, *args, **kwargs):
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
