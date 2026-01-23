"""Assembly module for shared bootstrap infrastructure.

Contains bootstrap functions for infrastructure components that are used by
both CLI and runtime contexts. These functions have no side-effects and
create pure infrastructure adapters.

Components:
- checkpoint: Checkpoint and quarantine port creation
- storage: Storage adapter assembly for I/O operations

Note:
    This module should NOT contain any NoOp implementations or CLI-specific
    logic. It provides neutral building blocks for higher-level bootstrap.
"""

from __future__ import annotations

from bioetl.composition.bootstrap.assembly.checkpoint import (
    # Deprecated aliases
    bootstrap_checkpoint,
    # Canonical names
    bootstrap_checkpoint_port,
    bootstrap_quarantine,
    bootstrap_quarantine_port,
)
from bioetl.composition.bootstrap.assembly.storage import (
    # Deprecated alias
    bootstrap_storage,
    # Canonical name
    bootstrap_storage_adapter,
)

__all__ = [
    # Deprecated aliases (backward compatibility)
    "bootstrap_checkpoint",
    # Canonical names (use these)
    "bootstrap_checkpoint_port",
    "bootstrap_quarantine",
    "bootstrap_quarantine_port",
    "bootstrap_storage",
    "bootstrap_storage_adapter",
]
